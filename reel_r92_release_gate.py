"""R92 offline gate for exact, owner-authorized first Reel and verified daily mode.

Never publishes by itself. Writes only GitHub job outputs. Actual upload and
publish still require current source artifact, fingerprint, history and Meta checks.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TORONTO=ZoneInfo("America/Toronto")
POLICY="owner_authorized_source_attribution_v1"


def gate(env, state, *, trigger=None, now=None):
    default={"enabled":False, "mode":"", "source_run_id":"", "approved_sha":""}
    if env.get("CURRENT_REF")!="refs/heads/main":
        return default
    if state.get("owner_authorized") is not True or state.get("policy")!=POLICY:
        return default
    event=env.get("EVENT_NAME")
    if event in ("push","workflow_dispatch"):
        source=(str(trigger.get("source_run_id","")) if event=="push" and isinstance(trigger,dict)
                else str(env.get("USER_SOURCE_RUN_ID","")))
        sha=(str(trigger.get("approved_video_sha256","")) if event=="push" and isinstance(trigger,dict)
             else str(env.get("USER_APPROVED_SHA","")))
        permitted=bool(
            state.get("controlled_first_live") is True
            and state.get("daily_enabled") is False
            and state.get("first_video_sha256")==sha
            and re.fullmatch(r"[a-f0-9]{64}",sha)
            and source.isdigit()
        )
        if event=="push":
            date=(now or datetime.now(TORONTO)).astimezone(TORONTO).date().isoformat()
            expected={"intent":"one-time-controlled-R72-first-live",
                      "toronto_date":date,
                      "source_run_id":source,
                      "approved_video_sha256":sha,
                      "publish_to_instagram":True}
            permitted=permitted and trigger==expected
        else:
            permitted=permitted and env.get("USER_CONFIRMATION")=="PUBLISH_VERIFIED_R72"
        return {"enabled":permitted,"mode":"first",
                "source_run_id":source,"approved_sha":sha}
    if event=="workflow_run":
        source=str(env.get("SOURCE_JOB_ID",""))
        verified=state.get("verified_first_media_id")
        enabled=(state.get("daily_enabled") is True
                 and state.get("controlled_first_live") is False
                 and isinstance(verified,str) and verified.isdigit()
                 and env.get("SOURCE_JOB_EVENT") in ("schedule","workflow_dispatch")
                 and env.get("SOURCE_JOB_CONCLUSION")=="success"
                 and env.get("SOURCE_JOB_BRANCH")=="main"
                 and env.get("SOURCE_JOB_REPO")==env.get("EXPECTED_REPO")
                 and bool(source.isdigit()))
        return {"enabled":enabled,"mode":"daily",
                "source_run_id":source,"approved_sha":""}
    return default


def main():
    env=dict(os.environ)
    state=json.loads(Path("r83_reel_autopublish_state.json").read_text())
    trigger=None
    if env.get("EVENT_NAME")=="push":
        file=Path(".github/r92-controlled-first-reel.trigger")
        if file.is_file():
            trigger=json.loads(file.read_text())
    result=gate(env,state,trigger=trigger)
    output=Path(os.environ["GITHUB_OUTPUT"])
    with output.open("a") as f:
        for key,value in result.items():
            f.write(f"{key}={str(value).lower() if isinstance(value,bool) else value}\n")
    print("R92 publishing gate:", "OPEN" if result["enabled"] else "LOCKED",
          "mode",result["mode"])


if __name__=="__main__":
    main()
