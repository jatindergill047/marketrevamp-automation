import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from publication_recovery import decision

class RecoveryTests(unittest.TestCase):
    def test_recovery(self):
        for month in (1, 7):
            now = datetime(2026, month, 14, 20, tzinfo=ZoneInfo("America/Toronto"))
            date = now.date().isoformat()
            for kind in ("reel", "carousel"):
                self.assertEqual(decision({}, kind, now), "recover")
                e = dict(toronto_date=date, media_kind=kind, status="published",
                         instagram_media_id="123", instagram_readback_verified=True)
                self.assertEqual(decision({"a": e}, kind, now), "skip")
                self.assertEqual(decision({"a": e, "b": e}, kind, now), "blocked")
                self.assertEqual(decision({"a": dict(e, status="pending")}, kind, now), "blocked")
                self.assertEqual(decision({"a": dict(e, status="failed", publish_attempted_at=1)}, kind, now), "blocked")
                self.assertEqual(decision({"a": dict(e, status="failed")}, kind, now), "recover")
                self.assertEqual(decision({"a": dict(e, toronto_date="2025-01-01")}, kind, now), "recover")
                self.assertEqual(decision(None, kind, now), "blocked")
                self.assertEqual(decision({}, kind, now.replace(hour=23)), "skip")
        weekend = datetime(2026, 11, 22, 20, tzinfo=ZoneInfo("America/Toronto"))
        self.assertEqual(decision({}, "carousel", weekend), "skip")
        self.assertEqual(decision({}, "reel", weekend), "recover")
