"""Allow manual runs, but run scheduled publishing only at 18:00 Toronto time."""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def should_run(event, now=None):
    if event != "schedule":
        return True
    now = now or datetime.now(ZoneInfo("America/Toronto"))
    return now.weekday() < 5 and now.hour == 18


if __name__ == "__main__":
    event = os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    allowed = should_run(event)
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write(f"run={'true' if allowed else 'false'}\n")
    print("Toronto schedule check:", "proceed" if allowed else "skip off-hour scheduled run")
