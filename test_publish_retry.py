"""Offline regression tests for safe Instagram retry boundaries."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_instagram as publisher


class PublishRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.manifest = root / "manifest.json"
        self.history = root / "history.json"
        self.manifest.write_text(json.dumps({
            "slides": [
                {"image_url": f"https://res.cloudinary.com/demo/image/upload/test{i}.jpg"}
                for i in range(7)
            ],
            "article_urls": [f"https://example.com/story{i}" for i in range(7)],
            "caption": "Sources: example.com",
            "first_comment": "#MarketRevamp #AI",
            "publish_enabled": True,
            "automated_checks_passed": True,
        }), encoding="utf-8")
        self.history.write_text("{}", encoding="utf-8")
        image_urls = [f"https://res.cloudinary.com/demo/image/upload/test{i}.jpg"
                      for i in range(7)]
        self.fingerprint = publisher.approval_fingerprint(
            json.loads(self.manifest.read_text(encoding="utf-8")), image_urls
        )
        self.saved = []
        def save(history):
            snapshot = json.loads(json.dumps(history))
            self.saved.append(snapshot)
            self.history.write_text(json.dumps(snapshot), encoding="utf-8")
        patches = [
            patch.object(publisher, "MANIFEST_FILE", self.manifest),
            patch.object(publisher, "HISTORY_FILE", self.history),
            patch.object(publisher, "PUBLISH_ENABLED", True),
            patch.object(publisher, "save_history", save),
            patch.object(publisher, "wait_for_container", lambda *_: None),
            patch.dict(publisher.os.environ, {
                "INSTAGRAM_PERSISTENCE_READY": "true",
                "INSTAGRAM_ACCESS_TOKEN": "FAKE",
                "INSTAGRAM_USER_ID": "FAKE_ACCOUNT",
                "INSTAGRAM_APPROVED_FINGERPRINT": self.fingerprint,
            }),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_unapproved_carousel_makes_no_api_requests(self):
        with patch.dict(publisher.os.environ, {
            "INSTAGRAM_APPROVED_FINGERPRINT": "not-the-current-carousel",
        }):
            with patch.object(publisher, "api_request") as api:
                publisher.main()
                api.assert_not_called()
        self.assertEqual(self.saved, [])

    def test_caption_change_invalidates_approval(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["caption"] = "Sources: different reviewed statement"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with patch.object(publisher, "api_request") as api:
            publisher.main()
            api.assert_not_called()
        self.assertEqual(self.saved, [])

    def test_prepublication_error_marks_failed_and_retry_succeeds(self):
        attempts = []
        def fake_api(method, endpoint, token, payload=None):
            attempts.append(endpoint)
            if endpoint.endswith("/media") and len(attempts) == 1:
                raise RuntimeError("media creation unavailable")
            if endpoint.endswith("/media_publish"):
                return {"id": "PUBLISHED"}
            return {"id": f"CONTAINER_{len(attempts)}"}
        with patch.object(publisher, "api_request", fake_api):
            with self.assertRaisesRegex(RuntimeError, "media creation unavailable"):
                publisher.main()
            record = next(iter(self.saved[-1].values()))
            self.assertEqual(record["status"], "failed")
            self.assertNotIn("publish_attempted_at", record)
            publisher.main()
        self.assertEqual(next(iter(self.saved[-1].values()))["status"], "published")
        self.assertEqual(sum(e.endswith("/media_publish") for e in attempts), 1)

    def test_ambiguous_publish_error_stays_pending_and_blocks_retry(self):
        calls = []
        def fake_api(method, endpoint, token, payload=None):
            calls.append(endpoint)
            if endpoint.endswith("/media_publish"):
                raise TimeoutError("publish response lost")
            return {"id": f"CONTAINER_{len(calls)}"}
        with patch.object(publisher, "api_request", fake_api):
            with self.assertRaisesRegex(TimeoutError, "publish response lost"):
                publisher.main()
            record = next(iter(self.saved[-1].values()))
            self.assertEqual(record["status"], "pending")
            self.assertIn("publish_attempted_at", record)
            publisher.main()
        self.assertEqual(sum(e.endswith("/media_publish") for e in calls), 1)

    def test_uncertain_first_comment_never_republishes(self):
        calls = []
        def fake_api(method, endpoint, token, payload=None):
            calls.append(endpoint)
            if endpoint.endswith("/media_publish"):
                return {"id": "PUBLISHED"}
            if endpoint.endswith("/comments"):
                raise TimeoutError("comment response was lost")
            return {"id": f"CONTAINER_{len(calls)}"}
        with patch.object(publisher, "api_request", fake_api):
            with self.assertRaisesRegex(RuntimeError, "do NOT republish"):
                publisher.main()
            record = next(iter(self.saved[-1].values()))
            self.assertEqual(record["status"], "published")
            self.assertEqual(record["first_comment_status"], "pending")
            publisher.main()
        self.assertEqual(sum(s.endswith("/media_publish") for s in calls), 1)
        self.assertEqual(sum(s.endswith("/comments") for s in calls), 1)

    def test_unknown_existing_status_blocks(self):
        with patch.object(publisher, "api_request") as api:
            import hashlib
            images = json.loads(self.manifest.read_text())["slides"]
            urls = [x["image_url"] for x in images]
            fingerprint = hashlib.sha256(json.dumps(urls, sort_keys=True).encode()).hexdigest()
            self.history.write_text(json.dumps({fingerprint: {"status": "pending"}}))
            publisher.main()
            api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
