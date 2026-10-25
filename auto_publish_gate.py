"""Validate an automatic Instagram publication against a successful prep run.

The preparation artifact is immutable. This script never contacts Instagram
and never accepts a reusable approval secret.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from publish_instagram import approval_fingerprint, load_manifest
from schedule_guard import valid_one_shot

TORONTO = ZoneInfo("America/Toronto")
TRIGGER = Path(".github/marketrevamp-post-now.trigger")


def toronto_today(now=None):
    return (now or datetime.now(TORONTO)).astimezone(TORONTO).date().isoformat()


def _set_env(key, value, destination=None):
    path = Path(destination or os.environ["GITHUB_ENV"])
    with path.open("a", encoding="utf-8") as out:
        out.write(f"{key}={value}\n")


def get_source(event, workflow_run_id="", trigger_path=TRIGGER, now=None):
    """Select a scheduled run, or one explicitly pinned one-shot push package."""
    if event == "workflow_run":
        if not re.fullmatch(r"[1-9][0-9]*", str(workflow_run_id)):
            raise ValueError("Missing successful scheduled run ID")
        return str(workflow_run_id), ""
    if event != "push":
        raise ValueError("Automatic publishing accepts only schedule completion or one-shot push")
    trigger = json.loads(Path(trigger_path).read_text(encoding="utf-8"))
    if trigger.get("toronto_date") != toronto_today(now):
        raise ValueError("One-shot trigger is for a different Toronto date")
    source = str(trigger.get("source_run_id", ""))
    expected = trigger.get("expected_fingerprint")
    if (not re.fullmatch(r"[1-9][0-9]*", source)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[a-f0-9]{64}", expected)):
        raise ValueError("Malformed one-shot source ID or fingerprint")
    return source, expected


def verify_preparation_run(data, source_run_id, repository, now=None):
    """Prevent cross-repo, off-date, manual, incomplete or stale source runs."""
    if (not isinstance(data, dict)
            or str(data.get("id")) != str(source_run_id)
            or data.get("name") != "MarketRevamp Automation"
            or data.get("event") not in ("schedule", "push")
            or data.get("head_branch") != "main"
            or data.get("conclusion") != "success"
            or (data.get("repository") or {}).get("full_name") != repository):
        raise ValueError("Preparation run provenance or conclusion invalid")
    stamp = datetime.fromisoformat(str(data["created_at"]).replace("Z", "+00:00"))
    if stamp.astimezone(TORONTO).date().isoformat() != toronto_today(now):
        raise ValueError("Refusing to publish an artifact from a previous Toronto date")
    if data.get("event") == "push" and not valid_one_shot(now):
        raise ValueError("One-shot live preparation lacks its valid Toronto-date marker")


def verify_manifest_and_fingerprint(expected=""):
    manifest, image_urls = load_manifest()
    if manifest.get("publish_enabled") is not True:
        raise ValueError("Preparation manifest disabled live publication")
    if manifest.get("automated_checks_passed") is not True:
        raise ValueError("Preparation automated checks did not pass")
    if len(manifest.get("article_urls", [])) != 7:
        raise ValueError("Expected exactly seven article URLs")
    if os.environ.get("REQUIRE_QUOTE_FIRST") == "true":
        if (manifest.get("quote_card_first") is not True
                or manifest.get("quote_card_count") != 1
                or not (manifest.get("slides") or [{}])[0].get(
                    "alt_text", "").startswith("MarketRevamp attributed quote card:")):
            raise ValueError("One-shot live package must have one verified quote on slide 1")
    fp = approval_fingerprint(manifest, image_urls)
    if expected and expected != fp:
        raise ValueError("One-shot artifact fingerprint changed; refusing publication")
    return fp


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode == "source":
        source, expected = get_source(
            os.environ["GITHUB_EVENT_NAME"],
            os.environ.get("PREPARATION_RUN_ID", ""),
        )
        _set_env("SOURCE_RUN_ID", source)
        _set_env("EXPECTED_REVIEW_FINGERPRINT", expected)
        print(f"Validated source run ID: {source}")
    elif mode == "verify-run":
        source = json.load(sys.stdin)
        verify_preparation_run(
            source, os.environ["SOURCE_RUN_ID"],
            os.environ["GITHUB_REPOSITORY"],
        )
        if source.get("event") == "push":
            _set_env("REQUIRE_QUOTE_FIRST", "true")
        print("Validated preparation branch, source event, completion, date and repository.")
    elif mode == "authorize":
        fp = verify_manifest_and_fingerprint(
            os.environ.get("EXPECTED_REVIEW_FINGERPRINT", "")
        )
        _set_env("INSTAGRAM_APPROVED_FINGERPRINT", fp)
        print(f"Automatic publication authorized for exact seven-image package: {fp}")
    else:
        raise ValueError("Expected source, verify-run or authorize")


if __name__ == "__main__":
    main()
