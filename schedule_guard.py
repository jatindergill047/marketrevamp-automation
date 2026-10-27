"""Toronto-local calendar guard for backup weekday schedules and dated pushes.

GitHub cron is UTC; schedule both EDT and EST offsets, then evaluate the
actual cron string with the Toronto date so an extra UTC trigger is ignored.
"""
import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
ONE_SHOT_DATES = {
    "2026-10-25": {
        "path": ".github/marketrevamp-live-20261025.trigger",
        "payload": {
            "toronto_date": "2026-10-25",
            "intent": "one-time-live-seven-news-quote-first",
            "max_quote_cards": 1,
            "quote_slide": 1,
            "attempt": 2,
        },
    },
    "2026-10-26": {
        "path": ".github/marketrevamp-live-20261026.trigger",
        "payload": {
            "toronto_date": "2026-10-26",
            "intent": "one-time-live-seven-news-standard",
            "max_quote_cards": 0,
            "attempt": 1,
        },
    },
}
# Backwards-compatible symbols for the reviewed October 25 test.
SINGLE_LIVE_DATE = "2026-10-25"
SINGLE_LIVE_TRIGGER = Path(ONE_SHOT_DATES[SINGLE_LIVE_DATE]["path"])

# Main attempt 18:13, missed-run backup 19:13 Toronto, Monday-Friday.
# 13 past the hour avoids GitHub's busiest :00 boundary.
SCHEDULE_MINUTE = 13
SCHEDULE_HOURS = (18, 19)


def one_shot_info(now=None):
    local = (now or datetime.now(TORONTO)).astimezone(TORONTO)
    return ONE_SHOT_DATES.get(local.date().isoformat())


def valid_one_shot(now=None, trigger_path=None):
    """Verify the date-specific payload, not just presence of a trigger file."""
    config = one_shot_info(now)
    if not config:
        return False
    path = Path(trigger_path) if trigger_path is not None else Path(config["path"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return payload == config["payload"]


def quote_first_for_one_shot(now=None):
    config = one_shot_info(now)
    return bool(config and config["payload"]["intent"].endswith("quote-first")
                and valid_one_shot(now))


def expected_crons(local):
    """Return the two matching UTC cron expressions for this Toronto day.

    Backup at 19:13 is on next UTC calendar day in EST, so its cron
    expression uses Tue-Sat rather than Mon-Fri.
    """
    result = set()
    for hour in SCHEDULE_HOURS:
        intended = local.replace(hour=hour, minute=SCHEDULE_MINUTE,
                                 second=0, microsecond=0)
        utc = intended.astimezone(timezone.utc)
        days = "2-6" if utc.date() != intended.date() else "1-5"
        result.add((f"{SCHEDULE_MINUTE} {utc.hour} * * {days}", intended))
    return result


def should_run(event, now=None, cron=None):
    if event == "push":
        return valid_one_shot(now)
    if event != "schedule":
        return True
    local = (now or datetime.now(TORONTO)).astimezone(TORONTO)
    if local.weekday() >= 5 or not (18 <= local.hour <= 21):
        return False
    if cron is None:
        # Tests or manual guard callers can inspect the operating window.
        return True
    for expected, intended in expected_crons(local):
        if cron.strip() == expected and intended <= local <= intended + timedelta(hours=3):
            return True
    return False


if __name__ == "__main__":
    event = os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    cron = os.getenv("MARKETREVAMP_SCHEDULE") if event == "schedule" else None
    allowed = should_run(event, cron=cron)
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write(f"run={'true' if allowed else 'false'}\n")
    print("Toronto schedule check:", "proceed" if allowed
          else "skip off-hours, incorrect DST cron or expired one-shot trigger")
