"""R49 fail-closed first-live Reel publishing tests. All network calls mocked."""
import datetime
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reel_r49_first_live import publish_once
from reel_r46_launch_gate import ReleaseBlocked

NOW = datetime.datetime(2026, 11, 20, 19, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))

def metadata():
    return {"toronto_date": "2026-11-20", "editorial_approved": True,
            "visual_qa_approved": True, "audio_qa_approved": True,
            "official_logo_verified": True, "word_timing_origin": "tts_word_boundaries",
            "voice": "en-US-AndrewNeural", "reviewed_by": "Human editor",
            "caption": "Seven reviewed news stories. Sources: all linked."}

def stories():
    return [{"headline": f"Headline {i}", "narration_text": f"Narration {i}",
             "source_url": f"https://example.org/news/{i}",
             "editorial_approved": True, "fact_check_status": "source_supported"}
            for i in range(7)]

CLOUDINARY_URL = "https://res.cloudinary.com/staging/video/upload/v1/reel.mp4"

class FirstLiveTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.video = Path(td.name) / "release.mp4"
        self.video.write_bytes(b"nonempty video bytes")
        probe = patch("reel_r46_launch_gate.video_info", return_value={
            "duration_seconds": 82.4, "width": 1080, "height": 1920
        })
        probe.start()
        self.addCleanup(probe.stop)
        flags = patch.dict(os.environ, {"REEL_FIRST_LIVE_ENABLED": "true",
                                       "INSTAGRAM_PUBLISH_ENABLED": "true",
                                       "REEL_UPLOAD_ENABLED": "true"})
        flags.start()
        self.addCleanup(flags.stop)

    def release_fp(self):
        from reel_r46_launch_gate import validate_and_fingerprint
        return validate_and_fingerprint(metadata(), stories(), self.video, now=NOW)["release_fingerprint"]

    def exercise(self, *, approval=None, history=None, uploader=None, request=None, saver=None,
                 meta=None, story_items=None, api_key="key", api_secret="secret"):
        return publish_once(meta or metadata(), story_items or stories(), self.video,
              {} if history is None else history,
              approved_fingerprint=self.release_fp() if approval is None else approval,
              cloud="staging", preset="reels-staging", account_id="123456789", token="token",
              api_key=api_key, api_secret=api_secret, uploader=uploader or
              (lambda *args: {"secure_url": CLOUDINARY_URL}),
              request=request or self.fake_success, saver=saver or (lambda h: None), now=NOW,
              sleep=lambda t: None)

    @staticmethod
    def fake_success(method, endpoint, token, payload):
        if method == "GET":
            return {"status_code": "FINISHED"}
        if endpoint.endswith("/media_publish"):
            return {"id": "191001"}
        return {"id": "190002"}

    def test_success_and_checkpoint_before_publish(self):
        checkpoints=[]
        calls=[]
        state={}
        def saver(h):
            checkpoints.append({k:v.copy() for k,v in h.items()})
        def request(method, endpoint, token, payload):
            if endpoint.endswith("/media_publish"):
                self.assertTrue(checkpoints[-1][self.release_fp()]["publish_attempted_at"])
                self.assertEqual(checkpoints[-1][self.release_fp()]["status"], "pending")
            calls.append((method,endpoint))
            return self.fake_success(method, endpoint, token, payload)
        response=self.exercise(history=state,request=request,saver=saver)
        self.assertEqual(response["status"], "published")
        self.assertEqual(state[self.release_fp()]["instagram_media_id"], "191001")
        self.assertEqual(len(checkpoints),4)
        self.assertEqual([c[0] for c in calls], ["POST", "GET", "POST"])

    def test_disabled_flag_blocks_network(self):
        with patch.dict(os.environ, {"REEL_FIRST_LIVE_ENABLED":"false"}):
            with self.assertRaisesRegex(ReleaseBlocked, "flag"):
                self.exercise(uploader=lambda *args: self.fail("Must not upload"))

    def test_mismatched_approval_blocks(self):
        with self.assertRaisesRegex(ReleaseBlocked, "approval"):
            self.exercise(approval="0"*64,uploader=lambda *args: self.fail("Must not upload"))

    def test_duplicate_article_blocks(self):
        history={"old":{"status":"published", "toronto_date":"2026-11-19",
                        "article_urls":["https://example.org/news/3"],
                        "media_kind":"carousel"}}
        with self.assertRaisesRegex(ReleaseBlocked, "Previously published"):
            self.exercise(history=history,uploader=lambda *args: self.fail("Must not upload"))

    def test_same_day_reel_blocks(self):
        history={"old":{"status":"pending", "toronto_date":"2026-11-20",
                        "media_kind":"reel"}}
        with self.assertRaisesRegex(ReleaseBlocked, "pending or completed"):
            self.exercise(history=history,uploader=lambda *args: self.fail("Must not upload"))

    def test_bad_cloudinary_url_blocks_instagram(self):
        with self.assertRaisesRegex(ReleaseBlocked, "Cloudinary URL"):
            self.exercise(uploader=lambda *args:{"secure_url":"https://evil.org/test.mp4"},
                          request=lambda *args:self.fail("Must not create container"))

    def test_ambiguous_publication_remains_pending(self):
        state={}
        checkpoints=[]
        def request(method, endpoint, token, payload):
            if endpoint.endswith("/media_publish"):
                raise TimeoutError("Unknown publishing outcome")
            return self.fake_success(method,endpoint,token,payload)
        def saver(h):
            checkpoints.append({k:v.copy() for k,v in h.items()})
        with self.assertRaises(TimeoutError):
            self.exercise(history=state,request=request,saver=saver)
        self.assertEqual(state[self.release_fp()]["status"],"pending")
        self.assertIn("publish_attempted_at",state[self.release_fp()])
        self.assertEqual(len(checkpoints),3)

    def test_unsigned_existing_cloudinary_preset_succeeds_when_fully_gated(self):
        # The production carousel already uses an unsigned upload preset.
        # R49 must support it without weakening video approval or history checks.
        uploaded=[]
        response=self.exercise(
            api_key="", api_secret="",
            uploader=lambda *args: (
                uploaded.append(args) or {"secure_url": CLOUDINARY_URL}
            ),
        )
        self.assertEqual(response["status"], "published")
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(uploaded[0][-2:], ("", ""))

    def test_partial_signed_cloudinary_secret_is_blocked(self):
        with self.assertRaisesRegex(ReleaseBlocked, "must both be supplied"):
            self.exercise(api_key="key", api_secret="",
                          uploader=lambda *args:self.fail("Must not upload"))

    def test_unapproved_editorial_rejected(self):
        m=metadata()
        m["editorial_approved"]=False
        with self.assertRaisesRegex(ReleaseBlocked, "Editorial"):
            self.exercise(meta=m, uploader=lambda *args:self.fail("Must not upload"))

if __name__=="__main__":
    unittest.main()
