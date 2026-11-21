"""Pure mocked R84 transport tests; never contact Cloudinary or Instagram."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import reel_r84_publish_job as job


class R84DeliveryTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name) / "release"
        self.root.mkdir()
        patcher = patch.object(job, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.fp = "a" * 64
        self.sha = "b" * 64
        (self.root / "release_gate.json").write_text(json.dumps({
            "fingerprint": self.fp,
            "video_sha256": self.sha,
            "first_live": True,
        }))
        self.release = {
            "fingerprint": self.fp, "video_sha256": self.sha,
            "first_live": True,
            "metadata": {"caption": "Source-linked, attributed"},
            "stories": [{"headline": "Sample"}] * 7,
        }
        self.state = {}
        for patcher in (
            patch.object(job, "release_data", return_value=self.release),
            patch.object(job, "read_json", side_effect=lambda p:
                         json.loads(Path(p).read_text()) if str(p).endswith("release_gate.json")
                         else {"controlled_first_live": True}),
            patch.object(job, "load_history", side_effect=lambda: self.state),
            patch.dict(os.environ, {
                "CLOUDINARY_CLOUD_NAME": "testcloud",
                "CLOUDINARY_UPLOAD_PRESET": "testpreset",
                "CLOUDINARY_API_KEY": "", "CLOUDINARY_API_SECRET": "",
                "INSTAGRAM_USER_ID": "1234567",
                "INSTAGRAM_ACCESS_TOKEN": "testsecret",
            })
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def fake_publisher(self, *args, **kwargs):
        self.assertEqual(kwargs["approved_fingerprint"], self.fp)
        self.assertEqual(kwargs["cloud"], "testcloud")
        self.assertEqual(kwargs["preset"], "testpreset")
        self.assertEqual(kwargs["account_id"], "1234567")
        self.state[self.fp] = {
            "status": "published", "instagram_media_id": "17812345",
            "media_kind": "reel", "toronto_date": "2026-11-21",
        }
        kwargs["saver"](self.state)
        return {"status": "published", "instagram_media_id": "17812345"}

    def test_success_requires_instagram_permalink_readback_and_history_checkpoint(self):
        saves=[]
        result=job.delivery(
            mode="first", expected_sha=self.sha,
            upload_and_publish=self.fake_publisher,
            request=lambda *args: {
                "id": "17812345", "media_type": "VIDEO",
                "permalink": "https://www.instagram.com/reel/ABC123/",
            },
            save=lambda history: saves.append(dict(history[self.fp]))
        )
        self.assertEqual(result["instagram_media_id"], "17812345")
        self.assertTrue(result["instagram_readback_verified"])
        self.assertEqual(len(saves), 2)
        self.assertTrue(saves[-1]["instagram_readback_verified"])
        self.assertEqual(saves[-1]["template_version"], "R72")
        self.assertEqual(saves[-1]["release_mode"], "first")
        self.assertTrue((self.root / "publication_result.json").is_file())

    def test_bad_instagram_readback_preserves_published_without_verification(self):
        saves=[]
        with self.assertRaisesRegex(RuntimeError, "readback"):
            job.delivery(
                mode="first", expected_sha=self.sha,
                upload_and_publish=self.fake_publisher,
                request=lambda *args: {
                    "id": "17812345", "media_type": "VIDEO",
                    "permalink": "https://example.com/not-instagram/",
                },
                save=lambda history: saves.append(dict(history[self.fp]))
            )
        self.assertEqual(len(saves), 1)
        self.assertEqual(saves[0]["status"], "published")
        self.assertFalse(saves[0].get("instagram_readback_verified", False))

    def test_prepared_release_cannot_be_swapped(self):
        (self.root / "release_gate.json").write_text(json.dumps({
            "fingerprint": "c"*64, "video_sha256": self.sha,
            "first_live": True,
        }))
        with self.assertRaisesRegex(RuntimeError, "fingerprint changed"):
            job.delivery(
                mode="first", expected_sha=self.sha,
                request=lambda *args: self.fail("no media GET"),
                upload_and_publish=lambda *args, **kwargs: self.fail("no upload"),
            )


if __name__ == "__main__":
    unittest.main()
