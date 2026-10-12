import json
from pathlib import Path

from publish_instagram import load_history, save_history

history = load_history()

test_key = "persistence-test"

history[test_key] = {
    "status": "test",
    "note": "GitHub history persistence verified",
}

save_history(history)

saved = json.loads(
    Path("publishing-history/instagram_publish_history.json")
    .read_text(encoding="utf-8")
)

assert saved.get(test_key, {}).get("status") == "test"

print("SUCCESS: Publishing history saved and verified.")
