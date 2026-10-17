"""Offline regression checks for MarketRevamp news scanner v2."""
import unittest

from news_quality import same_event, select_usable, source_domain, source_screen, independent_coverage


def article(title, category, rank):
    return {
        "title": title,
        "category": category,
        "url": f"https://example.com/story-{rank}",
        "published": "2026-10-16T15:00:00+00:00",
        "score": 30 - rank,
    }


GOOD_SUMMARY = (
    "The company's announcement described several changes affecting its "
    "products and customers. Executives provided new information about "
    "planned operations and explained the expected impact on the business. "
    "The company also outlined its immediate priorities for future work."
)


class NewsQualityTests(unittest.TestCase):
    def test_ai_incident_with_crypto_wallet_is_ai(self):
        from news_collector import infer_category
        story = article("OpenAI models hacked a crypto wallet and breached more websites", "Technology", 1)
        story["matched_categories"] = ["AI", "Crypto"]
        self.assertEqual(infer_category(story), "AI")

    def test_genuine_crypto_event_stays_crypto(self):
        from news_collector import infer_category
        story = article("Bitcoin ETF inflows surge as crypto exchanges report gains", "Technology", 1)
        story["matched_categories"] = ["Crypto", "Markets"]
        self.assertEqual(infer_category(story), "Crypto")

    def test_cybersecurity_without_ai_is_technology(self):
        from news_collector import infer_category
        story = article("Cybersecurity firm discovers malware targeting hospitals", "Technology", 1)
        story["matched_categories"] = ["Technology"]
        self.assertEqual(infer_category(story), "Technology")

    def test_event_duplicates(self):
        self.assertTrue(same_event(
            "Nvidia unveils new AI chip for enterprise data centers",
            "Nvidia unveils new AI chip for enterprise data centers today",
        ))
        self.assertFalse(same_event(
            "Bitcoin rises after Federal Reserve rate decision",
            "Bitcoin falls as exchange security breach emerges",
        ))
        self.assertFalse(same_event(
            "Markets rise", "Markets fall",
        ))

    def test_url_source(self):
        self.assertEqual(source_domain("https://www.cnbc.com/news"), "cnbc.com")

    def test_fallback_preserves_categories(self):
        items = [
            article("OpenAI releases new AI safety model", "AI", 1),
            article("Apple announces new smartphone chip", "Technology", 2),
            article("Bitcoin gains as traders study exchange balances", "Crypto", 3),
            article("Federal Reserve discusses Treasury yields", "Markets", 4),
            article("OpenAI announces enterprise AI safety research", "AI", 5),
            article("Crypto exchanges see renewed inflows", "Crypto", 6),
            article("Microsoft introduces new cloud software", "Technology", 7),
            article("Stock exchanges prepare new settlement system", "Markets", 8),
        ]
        # Highest-ranked AI article is unreadable; use the AI backup.
        def extract(url):
            if url.endswith("story-1"):
                return ""
            return "Valid original article text."

        result = select_usable(items, lambda s: s["category"],
                               extract, lambda t, headline: GOOD_SUMMARY)
        self.assertEqual(len(result), 7)
        self.assertEqual(len(set(s["url"] for s in result)), 7)
        self.assertTrue({"AI", "Technology", "Crypto", "Markets"} <= {
            s["selected_category"] for s in result
        })
        self.assertTrue(all(s["summary_status"] == "ready_for_review" for s in result))

    def test_different_urls_same_event_not_selected(self):
        items = [
            article("Nvidia unveils new AI chip for enterprise data centers", "AI", 1),
            article("Nvidia unveils new AI chip for enterprise data centers today", "AI", 2),
            article("Apple launches smartphone in major software event", "Technology", 3),
            article("Bitcoin advances as crypto markets stabilize", "Crypto", 4),
            article("Treasury yields rise after inflation numbers", "Markets", 5),
            article("Microsoft announces cloud update for developers", "Technology", 6),
            article("OpenAI publishes new research benchmark", "AI", 7),
            article("Ethereum developers ship blockchain upgrade", "Crypto", 8),
        ]
        result = select_usable(items, lambda s: s["category"],
                               lambda url: "Extracted article.",
                               lambda text, headline: GOOD_SUMMARY)
        self.assertEqual(len(result), 7)
        self.assertFalse(any(s["url"].endswith("story-2") for s in result))

    def test_independent_source_corroboration(self):
        one = {"title": "Nvidia unveils new AI chip for enterprise data centers",
               "url": "https://techcrunch.com/ai/new-chip"}
        two = {"title": "Nvidia unveils new AI chip for enterprise data centers today",
               "url": "https://www.bbc.com/news/new-chip"}
        same = {**two, "url": "https://techcrunch.com/another-new-chip"}
        matches = independent_coverage(one, [one, two, same])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["domain"], "bbc.com")
        self.assertFalse(source_screen(one, [one, two])["fact_checked"])

    def test_speculative_headlines_require_second_report(self):
        first = {"title": "Nvidia reportedly unveils new AI chip for data centers",
                 "url": "https://techcrunch.com/ai/chip"}
        second = {"title": "Nvidia reportedly unveils new AI chip for data centers today",
                  "url": "https://bbc.com/news/chip"}
        alone = source_screen(first, [first])
        self.assertTrue(alone["requires_independent_support"])
        self.assertFalse(alone["screening_passed"])
        self.assertTrue(source_screen(first, [first, second])["screening_passed"])
        confirmed = {"title": "Nvidia unveils new AI chip for data centers",
                     "url": "https://techcrunch.com/ai/chip"}
        self.assertTrue(source_screen(confirmed, [confirmed])["screening_passed"])
        self.assertEqual(source_screen(confirmed, [confirmed])["corroboration_status"], "single_source")

    def test_bbc_source_expansion(self):
        from news_collector import FEEDS, FEED_CATEGORY
        self.assertEqual(FEED_CATEGORY["BBC Technology"], "Technology")
        self.assertEqual(FEED_CATEGORY["BBC Business"], "Markets")
        self.assertTrue(FEEDS["BBC Technology"].startswith("https://feeds.bbci.co.uk/"))

    def test_insufficient_stories_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete carousel"):
            select_usable(
                [article("Apple announces product", "Technology", 1)],
                lambda x: x["category"],
                lambda url: "article", lambda text, headline: GOOD_SUMMARY
            )


if __name__ == "__main__":
    unittest.main()
