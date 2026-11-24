"""Read-only recovery decision; never changes history or contacts Instagram."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import sys

TORONTO = ZoneInfo("America/Toronto")

def decision(history, kind, now):
    local = now.astimezone(TORONTO)
    if kind not in ("reel", "carousel") or not isinstance(history, dict):
        return "blocked"
    if kind == "carousel" and local.weekday() >= 5:
        return "skip"
    if not 18 <= local.hour <= 22:
        return "skip"
    today = local.date().isoformat()
    matches = []
    for entry in history.values():
        if not isinstance(entry, dict) or not entry.get("toronto_date"):
            return "blocked"
        if entry.get("media_kind", "carousel") != kind:
            continue
        if entry.get("status") not in ("published", "failed") or (
            entry.get("status") == "failed" and
            (entry.get("publish_attempted_at") or entry.get("instagram_container_id"))
        ):
            return "blocked"
        if entry["toronto_date"] == today:
            matches.append(entry)
    published = [e for e in matches if e["status"] == "published"]
    if published:
        if len(published) != 1 or not str(published[0].get("instagram_media_id", "")).isdigit():
            return "blocked"
        if kind == "reel" and published[0].get("instagram_readback_verified") is not True:
            return "blocked"
        return "skip"
    return "recover"

if __name__ == "__main__":
    with open(sys.argv[2], encoding="utf-8") as f:
        result = decision(json.load(f), sys.argv[1], datetime.now(TORONTO))
    print(result)
    if result == "blocked":
        raise SystemExit(1)
