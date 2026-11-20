"""R47 offline smoke tests. Prove media_publish is never called."""
import os
import unittest
from unittest.mock import patch

from reel_r47_container_smoke import inspect_container, validate_staging

URL = "https://res.cloudinary.com/staging/video/upload/v1/test-reel.mp4"

class ContainerOnlyTests(unittest.TestCase):
    def test_staging_url_is_required(self):
        for bad in ("http://res.cloudinary.com/a/video/upload/test.mp4",
                    "https://example.org/video/upload/test.mp4",
                    "https://res.cloudinary.com/a/image/upload/test.png",
                    URL + "?access_token=secret"):
            with self.subTest(url=bad), self.assertRaises(ValueError):
                validate_staging(bad, "123456789", "token")

    def test_flags_fail_closed(self):
        for key in ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED"):
            with self.subTest(key=key), patch.dict(os.environ, {key: "true"}):
                with self.assertRaises(RuntimeError):
                    validate_staging(URL, "123456789", "token")

    def test_ready_container_never_publishes(self):
        called = []
        def mock(method, endpoint, token, data):
            called.append((method, endpoint, data))
            if method == "POST":
                return {"id": "178900001"}
            return {"status_code": "FINISHED"}
        result = inspect_container(URL, "123456789", "token", request=mock, pause=lambda _: None)
        self.assertEqual(result["status"], "FINISHED")
        self.assertFalse(result["instagram_published"])
        self.assertEqual([x[0] for x in called], ["POST", "GET"])
        self.assertTrue(all("media_publish" not in endpoint for _, endpoint, _ in called))
        self.assertEqual(called[0][2]["media_type"], "REELS")

    def test_error_fails_without_publication(self):
        calls = []
        def mock(method, endpoint, token, data):
            calls.append(endpoint)
            return {"id": "178900001"} if method == "POST" else {"status_code": "ERROR"}
        with self.assertRaisesRegex(RuntimeError, "processing failed"):
            inspect_container(URL, "123456789", "token", request=mock, pause=lambda _: None)
        self.assertTrue(all("media_publish" not in x for x in calls))

    def test_stuck_processing_fails_without_publication(self):
        def mock(method, endpoint, token, data):
            return {"id": "178900001"} if method == "POST" else {"status_code": "IN_PROGRESS"}
        with self.assertRaisesRegex(RuntimeError, "did not finish"):
            inspect_container(URL, "123456789", "token", request=mock,
                              pause=lambda _: None, max_polls=2)

if __name__ == "__main__":
    unittest.main()
