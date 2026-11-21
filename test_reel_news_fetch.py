"""No-network tests for bounded, publisher-host-preserving Reel extraction."""
import unittest
from unittest.mock import patch

from reel_news_fetch import (fetch_reel_article, limited_article_extractor,
                             ARTICLE_TIMEOUT_SECONDS, MAX_HTML_BYTES)


class Response:
    def __init__(self, url="https://www.techcrunch.com/news/story",
                 body=b"<html><body>Relevant publisher story.</body></html>",
                 content_type="text/html; charset=utf-8"):
        self.url=url
        self.body=body
        self.headers={"Content-Type":content_type}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def geturl(self):
        return self.url
    def read(self, length):
        assert length==MAX_HTML_BYTES+1
        return self.body


class BoundedReelArticleTests(unittest.TestCase):
    URL="https://techcrunch.com/news/story"

    def test_publisher_html_extracted_with_bounded_timeout(self):
        attempts=[]
        def opener(request, *, timeout):
            attempts.append((request.full_url,timeout))
            return Response()
        with patch("trafilatura.extract", return_value="Exact article content.") as parser:
            result=fetch_reel_article(self.URL,opener=opener)
        self.assertEqual(result,"Exact article content.")
        self.assertEqual(attempts,[(self.URL,ARTICLE_TIMEOUT_SECONDS)])
        self.assertTrue(parser.called)

    def test_cross_publisher_redirect_does_not_get_attributed(self):
        with patch("trafilatura.extract") as parser:
            result=fetch_reel_article(
                self.URL, opener=lambda *args,**kwargs:
                Response(url="https://otherpublisher.com/unrelated"))
            self.assertEqual(result,"")
            parser.assert_not_called()

    def test_wrong_content_type_and_oversize_blocked(self):
        self.assertEqual(fetch_reel_article(
            self.URL,opener=lambda *args,**kwargs:
            Response(content_type="application/pdf")),"")
        self.assertEqual(fetch_reel_article(
            self.URL,opener=lambda *args,**kwargs:
            Response(body=b"x"*(MAX_HTML_BYTES+1))),"")
        self.assertEqual(fetch_reel_article("http://techcrunch.com/x"),"")

    def test_http_timeout_skips_only_unresponsive_story(self):
        def failed(*args,**kwargs):
            raise TimeoutError("Publisher unavailable")
        self.assertEqual(fetch_reel_article(self.URL,opener=failed),"")

    def test_bounded_attempts_never_retry_unresponsive_sources(self):
        called=[]
        def fake(url):
            called.append(url)
            return ""
        extract=limited_article_extractor(max_attempts=2,fetcher=fake)
        self.assertEqual(extract("https://techcrunch.com/1"),"")
        self.assertEqual(extract("https://techcrunch.com/2"),"")
        self.assertEqual(extract("https://techcrunch.com/3"),"")
        self.assertEqual(len(called),2)
        with self.assertRaisesRegex(ValueError, "cap"):
            limited_article_extractor(max_attempts=41)


if __name__ == "__main__":
    unittest.main()
