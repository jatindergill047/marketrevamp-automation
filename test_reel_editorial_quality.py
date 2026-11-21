"""Regression: no duplicate Anthropic IPO, off-topic champagne copy, or forced gaps."""
import unittest
from reel_editorial_quality import (same_reel_event, summary_supports_headline,
                                    reel_story_guard)

IPO_ONE = "Anthropic’s record IPO collides with tech’s worst week on Wall Street since 2020"
IPO_TWO = "Why Anthropic's blockbuster IPO couldn't escape the stock market correction"
WRONG_DECK = ("Sake, vodka and Krug Champagne will be served. Each attendee will "
              "be given two jars of caviar. Investors had a party and celebrated "
              "with more food and drinks at a gathering after the event.")
RELEVANT_DECK = ("Anthropic's IPO had an unexpectedly difficult first week on the "
                 "public stock market after a wider correction. Company shares "
                 "also faced pressure from investors worried about valuations. "
                 "Further market reaction will depend on forthcoming company reports.")


class EditorialGuardTests(unittest.TestCase):
    def test_rejects_unrelated_extracted_article_paragraph(self):
        self.assertFalse(summary_supports_headline(IPO_ONE, WRONG_DECK))
        self.assertTrue(summary_supports_headline(IPO_ONE, RELEVANT_DECK))

    def test_same_named_ipo_identified_despite_different_wording(self):
        self.assertTrue(same_reel_event(IPO_ONE, IPO_TWO))
        self.assertFalse(same_reel_event("Meta emissions spike as data centers grow",
                                         "Meta releases a new virtual reality headset"))

    def test_prediction_markets_cftc_context_is_valid(self):
        headline = "State and federal battle over prediction markets regulation heats up"
        context = ("The CFTC moved to pause some Kalshi event contracts while "
                   "federal and state officials considered different restrictions "
                   "in recent meetings and court proceedings over potential manipulation "
                   "and investor and consumer safeguards.")
        self.assertTrue(summary_supports_headline(headline, context))

    def test_guard_refuses_duplicate_and_unrelated_but_allows_backup(self):
        chosen=[{"title": IPO_ONE, "summary": RELEVANT_DECK}]
        self.assertFalse(reel_story_guard(
            {"title": IPO_TWO, "summary": RELEVANT_DECK}, chosen))
        self.assertFalse(reel_story_guard(
            {"title": "Unrelated market headline", "summary": WRONG_DECK}, []))
        backup={"title": "Google updates its Android security architecture",
                "summary": ("Google says Android security updates now include new "
                            "protection features against account takeover and data "
                            "loss for certain phone customers this quarter, "
                            "according to a company briefing released to journalists "
                            "earlier in the week.")}
        self.assertTrue(reel_story_guard(backup, chosen))


if __name__ == "__main__":
    unittest.main()
