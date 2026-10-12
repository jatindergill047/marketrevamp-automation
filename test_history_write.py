import json
import time

from publish_instagram import load_history, save_history

history = load_history()

history["_connection_test"] = {
    "status": "test",
    "created_at": int(time.time()),
}

save_history(history)

print("SUCCESS: Publishing history saved to GitHub.")
