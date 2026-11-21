"""R107 strict offline narration regressions — never invoke Cloudinary or Meta."""
import unittest
from pathlib import Path

from reel_r107_narration import (
    additional_source_context, readable_subtitle_events, insert_story_pauses,
)


def cue(word, start, duration=.2):
    return {"text": word, "start_seconds": start, "duration_seconds": duration}


class NarrationPolishTests(unittest.TestCase):
    def test_context_is_verbatim_related_and_non_redundant(self):
        title = "Nvidia faces accounting inquiry"
        summary = (
            "Nvidia faces accounting inquiry. "
            "On Friday the regulators opened an inquiry into Nvidia's disclosures after reports of unusual inventory figures. "
            "A different unrelated sports result attracted millions of viewers."
        )
        # Relevance is independently checked by the existing headline guard.
        relevant = lambda h, s: "Nvidia" in s
        text = additional_source_context(summary, title, relevant)
        self.assertEqual(text, "On Friday the regulators opened an inquiry into Nvidia's disclosures after reports of unusual inventory figures.")
        self.assertIn(text, summary)
        self.assertEqual(additional_source_context(
            "Completely unrelated summary. No linked reporting.", title, relevant), "")

    def test_phonetic_spellings_are_invisible_but_timing_remains(self):
        events = [
            cue("an-THROP-ik's", 0.0, .8),
            cue("Naz-dak", 1.0, .4),
            cue("Open", 2.0), cue("A", 2.2), cue("I", 2.4),
            cue("B", 3.0), cue("T", 3.2), cue("C", 3.4),
            cue("S", 4.0), cue("and", 4.2), cue("P", 4.4),
            cue("five", 4.6), cue("hundred", 4.8),
            cue("unmodified", 5.5),
        ]
        before = [dict(e) for e in events]
        display = readable_subtitle_events(events)
        self.assertEqual([e["text"] for e in display],
                         ["Anthropic's", "Nasdaq", "OpenAI", "BTC", "S&P 500",
                          "unmodified"])
        self.assertEqual([e["start_seconds"] for e in display],
                         [0., 1., 2., 3., 4., 5.5])
        self.assertAlmostEqual(display[2]["duration_seconds"], .6)
        self.assertAlmostEqual(display[4]["duration_seconds"], 1.0)
        self.assertEqual(events, before, "Provider events must remain unmodified")

    def test_exact_eight_scene_pauses_retime_word_boundaries(self):
        events = [cue(f"word{i}", float(i), .2) for i in range(10)]
        recorded = []
        def run(command, **kw):
            recorded.append(command)
        new = insert_story_pauses(
            Path("source.mp3"), Path("spaced.wav"), events,
            list(range(9)), probe=lambda p: {"format": {"duration": "10.0"}},
            run=run)
        self.assertEqual(len(recorded), 1)
        filter_graph = recorded[0][recorded[0].index("-filter_complex") + 1]
        self.assertIn("concat=n=17:v=0:a=1", filter_graph)
        self.assertEqual(filter_graph.count("anullsrc"), 8)
        self.assertAlmostEqual(new[0]["start_seconds"], 0)
        self.assertAlmostEqual(new[1]["start_seconds"], 1.16)
        self.assertAlmostEqual(new[8]["start_seconds"], 9.28)
        self.assertEqual(events[8]["start_seconds"], 8)

    def test_invalid_chapters_refused_before_any_ffmpeg(self):
        called = []
        with self.assertRaises(ValueError):
            insert_story_pauses(
                "narration.mp3", "out.wav",
                [cue("A", 0.0), cue("B", 1.0)], [0, 1],
                probe=lambda p: {"format": {"duration": "4"}},
                run=lambda *a, **k: called.append(True))
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
