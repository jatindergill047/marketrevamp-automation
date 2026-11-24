import unittest
from publication_readback import reconcile

class ReadbackTests(unittest.TestCase):
    def test_exact_id(self):
        h = {"a": {"status": "pending", "media_kind": "reel", "instagram_media_id": "123"}}
        def get(method, endpoint, token, payload):
            self.assertEqual((method, endpoint), ("GET", "123"))
            return {"id": "123", "media_type": "VIDEO", "permalink": "https://www.instagram.com/reel/example/"}
        self.assertTrue(reconcile(h, get, "fake"))
        self.assertTrue(h["a"]["instagram_readback_verified"])
        self.assertFalse(reconcile(h, get, "fake"))

    def test_unknown_id(self):
        h = {"a": {"status": "pending", "instagram_container_id": "123"}}
        self.assertFalse(reconcile(h, lambda *a: self.fail("Unexpected API call"), "fake"))
        self.assertEqual(h["a"]["status"], "pending")

    def test_mismatch(self):
        h = {"a": {"status": "pending", "instagram_media_id": "123"}}
        self.assertFalse(reconcile(h, lambda *a: {"id": "456", "media_type": "CAROUSEL_ALBUM", "permalink": "https://instagram.com/p/example/"}, "fake"))
        self.assertEqual(h["a"]["status"], "pending")
