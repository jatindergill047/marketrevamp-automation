"""Offline regression checks for MarketRevamp news scanner v2."""
import unittest

from news_quality import same_event, select_usable, source_domain, source_screen, independent_coverage, screen_summary


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

    def test_summary_requires_exact_publisher_support(self):
        self.assertTrue(screen_summary(GOOD_SUMMARY, GOOD_SUMMARY)["passed"])
        altered = GOOD_SUMMARY.replace("several changes", "unverified profits")
        self.assertEqual(screen_summary(altered, GOOD_SUMMARY)["reason"],
                         "summary_not_in_source")

    def test_unattributed_privacy_allegation_is_held(self):
        first = ("Some Ray-Ban Meta glasses were recording private conversations "
                 "without the wearer knowing.")
        attributed = ("According to user reports, some Ray-Ban Meta glasses "
                      "were recording conversations unexpectedly.")
        self.assertEqual(screen_summary(first, first)["reason"],
                         "unattributed_sensitive_claim")
        self.assertTrue(screen_summary(attributed, attributed)["passed"])

    def test_selection_skips_unattributed_story_and_uses_backup(self):
        items = [
            article("Ray-Ban Meta glasses record conversations without consent", "Technology", 1),
        ] + [article(title, "AI", i) for i, title in enumerate((
            "Nvidia introduces new chip architecture",
            "Microsoft expands cloud data center capacity",
            "Apple announces accessibility software",
            "Google releases developer tools",
            "Anthropic publishes research evaluation",
            "Amazon announces robotics investment",
            "Tesla upgrades autonomous driving systems",
            "OpenAI releases education product",
        ), start=2)]
        risky = ("Some Ray-Ban Meta glasses were recording private conversations "
                 "without the wearer knowing.")
        def extract(url):
            return risky if url.endswith("story-1") else GOOD_SUMMARY
        def summarize(text, headline):
            return text
        result = select_usable(items, lambda x: x["category"], extract, summarize)
        self.assertEqual(len(result), 7)
        self.assertFalse(any(x["url"].endswith("story-1") for x in result))
        self.assertTrue(all(x["summary_screening"]["passed"] for x in result))
        self.assertTrue(all(not x["fact_checked"] for x in result))

    def test_joined_article_heading_removed_without_rewriting_claim(self):
        from news_collector import _sentence_candidates
        from news_quality import strip_section_heading
        raw = ("Unanswered questions Meta hasn’t said what caused the "
               "Ray-Ban Metas to record people without user consent. "
               "According to user reports, the smart glasses recorded "
               "conversations unexpectedly in several instances.")
        candidates = _sentence_candidates(raw, "Ray-Ban Meta smart glasses report")
        self.assertTrue(candidates)
        self.assertTrue(candidates[0][1].startswith("Meta hasn’t said"))
        self.assertNotIn("Unanswered questions", candidates[0][1])
        self.assertEqual(strip_section_heading("Unanswered questions remain."),
                         "Unanswered questions remain.")
        self.assertEqual(screen_summary(raw.split(". ")[0] + ".", raw)["reason"],
                         "embedded_section_heading")
        self.assertTrue(screen_summary(candidates[0][1], raw)["passed"])

    def test_section_heading_kept_out_of_generated_summary(self):
        from news_collector import generate_summary
        raw = ("Unanswered questions Meta hasn’t said what caused the "
               "Ray-Ban Metas to record people without user consent. "
               "According to user reports, the smart glasses recorded "
               "conversations unexpectedly in several instances. "
               "The company said it was reviewing reports from customers "
               "and investigating the behavior of the devices.")
        summary = generate_summary(raw, headline="Ray-Ban Meta glasses recording issue")
        self.assertTrue(summary)
        self.assertNotIn("Unanswered questions", summary)
        self.assertTrue(screen_summary(summary, raw)["passed"])

    def test_repeated_research_firm_description_is_not_used_twice(self):
        from news_collector import generate_summary
        from news_quality import repeated_descriptive_phrase
        lead = (
            "The influential research firm says real-world assets could finally "
            "give blockchains a clear role in finance."
        )
        detail = (
            "For investors, the next challenge is figuring out which companies, "
            "networks and protocols capture the revenue."
        )
        repetitive = (
            "Now, an influential research firm that Wall Street investors pay "
            "attention to has made the case for them."
        )
        later = (
            "Tokenization would allow financial institutions to represent asset "
            "ownership using programmable digital records."
        )
        article_text = " ".join((lead, detail, repetitive, later))
        self.assertTrue(repeated_descriptive_phrase(lead, repetitive))
        self.assertEqual(
            screen_summary(lead + " " + repetitive, article_text)["reason"],
            "repeated_descriptive_phrase",
        )
        summary = generate_summary(
            article_text, min_words=30, max_words=75,
            headline="Citrini sees a tokenization boom",
        )
        self.assertTrue(summary)
        self.assertLessEqual(summary.casefold().count("influential research firm"), 1)
        self.assertTrue(screen_summary(summary, article_text)["passed"])

    def test_new_numbered_detail_can_restate_subject(self):
        from news_quality import repeated_descriptive_phrase
        a = "The influential research firm outlined a broad strategy for digital assets."
        b = "The influential research firm expects 30 companies to adopt the software."
        self.assertFalse(repeated_descriptive_phrase(a, b))
        self.assertTrue(screen_summary(a + " " + b, a + " " + b)["passed"])

    def test_summary_sentences_stay_within_nearby_article_sections(self):
        from news_collector import _sentence_candidates, generate_summary
        opening = (
            "Nvidia announced a new AI processor for enterprise customers during "
            "its annual developer conference."
        )
        middle = [
            f"Background section {i} describes unrelated historical details about "
            "the industry and its changing business conditions."
            for i in range(8)
        ]
        ending = (
            "Nvidia said the new AI processor would reach enterprise customers "
            "through its hardware partners later this year."
        )
        article_text = " ".join([opening, *middle, ending])
        summary = generate_summary(article_text, min_words=20, max_words=70,
                                   headline="Nvidia new AI processor enterprise")
        if summary:
            candidates = _sentence_candidates(article_text,
                                              "Nvidia new AI processor enterprise")
            positions = [position for position, sentence, _, _ in candidates
                         if sentence in summary]
            self.assertGreaterEqual(len(positions), 2)
            self.assertTrue(all(b - a <= 5 for a, b in zip(positions, positions[1:])))

    def test_publisher_diversity_when_sources_available(self):
        titles = [
            "Nvidia introduces next generation chip platform",
            "Microsoft launches cloud computing service",
            "Apple reveals new mobile operating system",
            "Google expands enterprise search features",
            "Amazon unveils logistics robotics platform",
            "Tesla releases new battery technology",
            "Bitcoin exchange adds custody safeguards",
            "Ethereum developers approve network proposal",
            "Federal Reserve updates inflation forecast",
            "European markets respond to economic report",
        ]
        items = []
        for i, title in enumerate(titles):
            item = article(title, "Technology", i + 1)
            domain = ("first.com" if i < 5 else
                      "second.com" if i < 8 else "third.com")
            item["url"] = f"https://{domain}/story-{i}"
            items.append(item)
        chosen = select_usable(items, lambda x: x["category"],
                               lambda url: GOOD_SUMMARY,
                               lambda text, headline: GOOD_SUMMARY)
        from collections import Counter
        counts = Counter(source_domain(x["url"]) for x in chosen)
        self.assertEqual(len(chosen), 7)
        self.assertLessEqual(max(counts.values()), 3)

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
            return GOOD_SUMMARY

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
                               lambda url: GOOD_SUMMARY,
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

    def test_syndicated_reprint_is_not_independent_coverage(self):
        primary = {
            "title": "Nvidia unveils new AI chip for enterprise data centers",
            "url": "https://wire.example/story",
        }
        mirror = {
            "title": "Nvidia unveils new AI chip for enterprise data centers today",
            "url": "https://publisher.example/reprint",
            "original_source_url": "https://wire.example/story",
        }
        self.assertEqual(independent_coverage(primary, [primary, mirror]), [])
        self.assertEqual(source_screen(primary, [primary, mirror])["corroboration_status"],
                         "single_source")
        independent = {
            **mirror,
            "url": "https://independent.example/report",
            "original_source_url": "https://independent.example/report",
        }
        self.assertEqual(len(independent_coverage(primary, [primary, mirror, independent])), 1)

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
