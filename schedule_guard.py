"""Run only the matching 18:00 Toronto schedule (EDT or EST), not both."""
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
SINGLE_LIVE_DATE = "2026-10-25"
SINGLE_LIVE_TRIGGER = Path(".github/marketrevamp-live-20261025.trigger")


def valid_one_shot(now=None, trigger_path=SINGLE_LIVE_TRIGGER):
    """Explicit dated quote-first push; ordinary pushes never prepare news."""
    local = (now or datetime.now(TORONTO)).astimezone(TORONTO)
    if local.date().isoformat() != SINGLE_LIVE_DATE:
        return False
    try:
        payload = json.loads(Path(trigger_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return payload == {
        "toronto_date": SINGLE_LIVE_DATE,
        "intent": "one-time-live-seven-news-quote-first",
        "max_quote_cards": 1,
        "quote_slide": 1,
    }



def should_run(event, now=None, cron=None):
    if event == "push":
        return valid_one_shot(now)
    if event != "schedule":
        return True
    now = now or datetime.now(TORONTO)
    local = now.astimezone(TORONTO)
    if local.weekday() >= 5 or not 18 <= local.hour <= 21:
        return False
    if cron is not None:
        # Only one of 22:00 and 23:00 UTC corresponds to 18:00 Toronto
        # on a given date. Respect the originating cron even if GH is late.
        intended = local.replace(hour=18, minute=0, second=0, microsecond=0)
        utc_hour = intended.astimezone(timezone.utc).hour
        return cron.strip() == f"0 {utc_hour} * * 1-5"
    return True


if __name__ == "__main__":
    event = os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    cron = os.getenv("MARKETREVAMP_SCHEDULE") if event == "schedule" else None
    allowed = should_run(event, cron=cron)
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write(f"run={'true' if allowed else 'false'}\n")
    print("Toronto schedule check:", "proceed" if allowed else "skip off-hour, invalid date, or duplicate cron")
