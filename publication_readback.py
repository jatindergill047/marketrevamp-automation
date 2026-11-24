"""Reconcile only exact known Instagram media IDs; never publish or guess."""
from urllib.parse import urlsplit
import time

def reconcile(history, request, token):
    changed = False
    for record in history.values():
        if record.get("status") not in ("pending", "published"):
            continue
        if record.get("instagram_readback_verified") is True:
            continue
        media_id = str(record.get("instagram_media_id", ""))
        if not media_id.isdigit():
            continue
        kind = record.get("media_kind", "carousel")
        expected = {"reel": "VIDEO", "carousel": "CAROUSEL_ALBUM"}.get(kind)
        if not expected:
            continue
        result = request("GET", media_id, token, {"fields": "id,media_type,permalink"})
        url = urlsplit(str(result.get("permalink", "")))
        if (str(result.get("id")) != media_id or result.get("media_type") != expected
                or url.scheme != "https" or url.hostname not in ("instagram.com", "www.instagram.com")):
            continue
        record.update(status="published", instagram_readback_verified=True,
                      instagram_permalink=result["permalink"], instagram_verified_at=int(time.time()))
        changed = True
    return changed

if __name__ == "__main__":
    import os
    from publish_instagram import api_request, load_history, save_history
    history = load_history()
    if reconcile(history, api_request, os.environ["INSTAGRAM_ACCESS_TOKEN"]):
        save_history(history)
