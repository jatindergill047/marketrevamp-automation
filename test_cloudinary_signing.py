"""Offline signed Cloudinary upload regression checks."""
import hashlib
import unittest

from upload_to_cloudinary import upload_fields


class CloudinarySigningTests(unittest.TestCase):
    def test_signed_payload_matches_cloudinary_sha1_contract(self):
        fields = dict(upload_fields("marketrevamp", "key123", "secret123", timestamp=1700000000))
        expected = hashlib.sha1(
            b"timestamp=1700000000&upload_preset=marketrevampsecret123"
        ).hexdigest()
        self.assertEqual(fields["signature"], expected)
        self.assertEqual(fields["api_key"], "key123")
        self.assertEqual(fields["timestamp"], "1700000000")

    def test_unsigned_legacy_fallback(self):
        self.assertEqual(upload_fields("marketrevamp"), [("upload_preset", "marketrevamp")])

    def test_partial_credentials_fail_closed(self):
        with self.assertRaises(ValueError):
            upload_fields("marketrevamp", api_key="key")
        with self.assertRaises(ValueError):
            upload_fields("marketrevamp", api_secret="secret")


if __name__ == "__main__":
    unittest.main()
