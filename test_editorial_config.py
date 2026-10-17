"""Check editorial config remains valid and shared by the collector."""
import unittest

import editorial_config as config
import news_collector as collector


class EditorialConfigTests(unittest.TestCase):
    def test_shared_configuration_aliases(self):
        for name in (
            "FEEDS", "FEED_CATEGORY", "HEADERS", "KEYWORDS", "EXCLUDE",
            "SUMMARY_MIN_WORDS", "SUMMARY_MAX_WORDS",
        ):
            self.assertIs(getattr(collector, name), getattr(config, name))

    def test_required_topic_coverage_and_minimum_word_bounds(self):
        categories = {"AI", "Technology", "Crypto", "Markets"}
        self.assertTrue(categories.issubset(config.KEYWORDS))
        self.assertTrue(categories.issubset(config.FEEDS))
        self.assertTrue(all(config.KEYWORDS[category] for category in categories))
        self.assertTrue(all(str(url).startswith("https://")
                            for url in config.FEEDS.values()))
        self.assertTrue(1 <= config.SUMMARY_MIN_WORDS <= config.SUMMARY_MAX_WORDS)
        self.assertTrue(config.HEADERS["User-Agent"].startswith("MarketRevamp"))


if __name__ == "__main__":
    unittest.main()
