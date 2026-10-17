"""Offline regression tests for safe Instagram retry boundaries."""
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
            "publish_enabled": True,
            "automated_checks_passed": True,
        }), encoding="utf-8")
        self.history.write_text("{}", encoding="utf-8")
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
            }),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

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

    def test_unknown_existing_status_blocks(self):
        with patch.object(publisher, "api_request") as api:
            publisher.main() if False else None
            import hashlib
            images = json.loads(self.manifest.read_text())["slides"]
            urls = [x["image_url"] for x in images]
            fingerprint = hashlib.sha256(json.dumps(urls, sort_keys=True).encode()).hexdigest()
            self.history.write_text(json.dumps({fingerprint: {"status": "pending"}}))
            publisher.main()
            api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
