"""No-network regression for transient Edge Neural speech failure recovery."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reel_r72_review import synthesize_with_retry


class R97NeuralRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_failures_clean_partial_media_before_success(self):
        with tempfile.TemporaryDirectory() as root:
            audio=Path(root)/"audio.mp3"
            boundaries=Path(root)/"word_boundaries.json"
            count=[]
            delays=[]
            async def fake_synthesize(text, destination, events_path, **kwargs):
                count.append(1)
                self.assertEqual(kwargs["min_events"],80)
                if len(count)<3:
                    destination.write_bytes(b"PARTIAL")
                    events_path.write_text("[]")
                    raise OSError("Temporarily unavailable")
                self.assertFalse(destination.exists())
                self.assertFalse(events_path.exists())
                destination.write_bytes(b"COMPLETE")
                events_path.write_text("[]")
                return [{"type":"WordBoundary"}] * 80
            async def fake_sleep(delay):
                delays.append(delay)
            with patch("reel_r72_review.synthesize", fake_synthesize):
                result=await synthesize_with_retry("fixed spoken script",audio,boundaries,
                                                   sleep=fake_sleep)
            self.assertEqual(len(count),3)
            self.assertEqual(delays,[4,8])
            self.assertEqual(len(result),80)
            self.assertEqual(audio.read_bytes(),b"COMPLETE")

    async def test_fails_closed_after_three_audio_failures(self):
        with tempfile.TemporaryDirectory() as root:
            audio=Path(root)/"audio.mp3"
            boundaries=Path(root)/"word_boundaries.json"
            count=[]
            async def bad(*args,**kwargs):
                count.append(1)
                audio.write_bytes(b"PARTIAL")
                boundaries.write_text("[]")
                raise TimeoutError("Transient voice service timeout")
            async def no_wait(seconds):
                pass
            with patch("reel_r72_review.synthesize",bad):
                with self.assertRaises(TimeoutError):
                    await synthesize_with_retry("script",audio,boundaries,
                                                sleep=no_wait)
            self.assertEqual(len(count),3)
            self.assertFalse(audio.exists())
            self.assertFalse(boundaries.exists())


if __name__=="__main__":
    unittest.main()
