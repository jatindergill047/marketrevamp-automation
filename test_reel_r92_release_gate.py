"""R92 GitHub release-gate tests. No media publishing/network calls."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from reel_r92_release_gate import gate, POLICY

NOW=datetime(2026,11,21,16,0,tzinfo=ZoneInfo("America/Toronto"))
SHA="a"*64
STATE={"owner_authorized":True,"policy":POLICY,
       "controlled_first_live":False,"first_video_sha256":None,
       "daily_enabled":False,"verified_first_media_id":None}
BASE={"CURRENT_REF":"refs/heads/main","EXPECTED_REPO":"jatindergill047/marketrevamp-automation"}
TRIGGER={"intent":"one-time-controlled-R72-first-live",
         "toronto_date":"2026-11-21","source_run_id":"44948095529",
         "approved_video_sha256":SHA,"publish_to_instagram":True}


class R92GateTests(unittest.TestCase):
    def test_disabled_by_default_even_owner_authorized(self):
        s={**STATE}
        self.assertFalse(gate({**BASE,"EVENT_NAME":"push"},s,
                              trigger=TRIGGER,now=NOW)["enabled"])
        self.assertFalse(gate({**BASE,"EVENT_NAME":"workflow_run"},s,now=NOW)["enabled"])

    def test_first_live_hash_source_and_date_binding(self):
        s={**STATE,"controlled_first_live":True,"first_video_sha256":SHA}
        e={**BASE,"EVENT_NAME":"push"}
        result=gate(e,s,trigger=TRIGGER,now=NOW)
        self.assertTrue(result["enabled"])
        self.assertEqual(result["mode"],"first")
        self.assertEqual(result["approved_sha"],SHA)
        for bad in (
            {**TRIGGER,"toronto_date":"2026-11-20"},
            {**TRIGGER,"approved_video_sha256":"b"*64},
            {**TRIGGER,"source_run_id":"not-run"},
            {**TRIGGER,"publish_to_instagram":False},
            {**TRIGGER,"extra":"unknown"},
        ):
            self.assertFalse(gate(e,s,trigger=bad,now=NOW)["enabled"])
        self.assertFalse(gate(e,s,trigger=TRIGGER,
                              now=NOW.replace(day=22))["enabled"])
        self.assertFalse(gate({**e,"CURRENT_REF":"refs/heads/feature"},
                              s,trigger=TRIGGER,now=NOW)["enabled"])

    def test_dispatch_requires_manual_confirmation(self):
        s={**STATE,"controlled_first_live":True,"first_video_sha256":SHA}
        e={**BASE,"EVENT_NAME":"workflow_dispatch",
           "USER_SOURCE_RUN_ID":"44948095529","USER_APPROVED_SHA":SHA}
        self.assertFalse(gate(e,s,now=NOW)["enabled"])
        self.assertTrue(gate({**e,"USER_CONFIRMATION":"PUBLISH_VERIFIED_R72"},
                             s,now=NOW)["enabled"])

    def test_recurring_requires_first_verification_and_production_run(self):
        e={**BASE,"EVENT_NAME":"workflow_run","SOURCE_JOB_ID":"44948095529",
           "SOURCE_JOB_EVENT":"schedule","SOURCE_JOB_BRANCH":"main",
           "SOURCE_JOB_CONCLUSION":"success",
           "SOURCE_JOB_REPO":BASE["EXPECTED_REPO"],
           "SOURCE_ARTIFACT_VERIFIED":"true"}
        s={**STATE,"daily_enabled":True,
           "verified_first_media_id":"1788000111222333"}
        self.assertTrue(gate(e,s,now=NOW)["enabled"])
        self.assertFalse(gate({**e,"SOURCE_JOB_CONCLUSION":"failure"},
                              s,now=NOW)["enabled"])
        self.assertFalse(gate({**e,"SOURCE_ARTIFACT_VERIFIED":"false"},
                              s,now=NOW)["enabled"])
        self.assertFalse(gate({**e,"SOURCE_ARTIFACT_VERIFIED":""},
                              s,now=NOW)["enabled"])
        self.assertFalse(gate({**e,"SOURCE_JOB_REPO":"attacker/clone"},
                              s,now=NOW)["enabled"])
        self.assertFalse(gate(e,{**s,"controlled_first_live":True},now=NOW)["enabled"])
        self.assertFalse(gate(e,{**s,"verified_first_media_id":None},now=NOW)["enabled"])


if __name__=="__main__":
    unittest.main()
