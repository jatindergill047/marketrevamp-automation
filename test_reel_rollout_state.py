"""No-network state transitions for MarketRevamp Reel publishing."""
import unittest
from reel_rollout_state import rollout_state_valid

SHA="a"*64
BASE={"policy":"owner_authorized_source_attribution_v1",
      "owner_authorized":True,
      "controlled_first_live":False,
      "daily_enabled":False,
      "first_video_sha256":None,
      "verified_first_media_id":None}


class RolloutStateTests(unittest.TestCase):
    def test_disabled_status_default(self):
        self.assertEqual(rollout_state_valid(BASE),"disabled")

    def test_first_live_requires_exact_hash(self):
        live={**BASE,"controlled_first_live":True,
              "first_video_sha256":SHA}
        self.assertEqual(rollout_state_valid(live),"first")
        for bad in (
            {**live,"first_video_sha256":"xyz"},
            {**live,"daily_enabled":True},
            {**live,"verified_first_media_id":"178123"},
        ):
            with self.assertRaises(ValueError):
                rollout_state_valid(bad)

    def test_daily_requires_verified_first_id_and_sha(self):
        active={**BASE,"daily_enabled":True,
                "first_video_sha256":SHA,
                "verified_first_media_id":"17878336866585252"}
        self.assertEqual(rollout_state_valid(active),"daily")
        for bad in (
            {**active,"verified_first_media_id":None},
            {**active,"first_video_sha256":None},
            {**active,"controlled_first_live":True},
        ):
            with self.assertRaises(ValueError):
                rollout_state_valid(bad)

    def test_cannot_enable_without_owner(self):
        with self.assertRaisesRegex(ValueError, "Owner"):
            rollout_state_valid({**BASE,"owner_authorized":False})


if __name__=="__main__":
    unittest.main()
