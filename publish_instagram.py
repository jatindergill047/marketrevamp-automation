"""Fail-closed Instagram carousel publishing with persistent history."""

from carousel_config import CAROUSEL_SIZE

import json
import os
import sys
import time
import hashlib
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from urllib.parse import urlsplit, urlunsplit

# Review the Meta Graph API version and deprecation schedule quarterly.
# Do not guess a sunset date; confirm against Meta release notes.
API_VERSION = "v24.0"
API_BASE = f"https://graph.instagram.com/{API_VERSION}"

MANIFEST_FILE = Path("instagram_carousel_manifest.json")
HISTORY_FILE = Path("instagram_publish_history.json")

PUBLISH_ENABLED = (
    os.getenv("INSTAGRAM_PUBLISH_ENABLED", "false").lower() == "true"
)

def normalize_article_url(url):
    """Normalize article URLs for duplicate detection."""
    if not isinstance(url, str):
        raise ValueError("Invalid article URL.")

    parts = urlsplit(url.strip())

    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("Invalid article URL.")

    return urlunsplit((
        "https",
        parts.netloc.lower(),
        parts.path.rstrip("/") or "/",
        "",
        ""
    ))

def load_history():
    if not HISTORY_FILE.exists():
        raise RuntimeError("Publishing history is missing.")

    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))

    if not isinstance(history, dict):
        raise RuntimeError("Invalid publishing history.")

    return history



def merge_history_updates(base, proposed, remote):
    """Merge disjoint Git history updates; reject conflicting records.

    Never infer a safe winner for two distinct updates to the same
    fingerprint. Missing or malformed records also fail closed.
    """
    if any(not isinstance(data, dict) for data in (base, proposed, remote)):
        raise RuntimeError("Cannot reconcile malformed publishing history.")
    sentinel = object()
    merged = {}
    for key in base.keys() | proposed.keys() | remote.keys():
        old = base.get(key, sentinel)
        ours = proposed.get(key, sentinel)
        theirs = remote.get(key, sentinel)
        if not isinstance(key, str) or any(
            value is not sentinel and not isinstance(value, dict)
            for value in (old, ours, theirs)
        ):
            raise RuntimeError("Cannot reconcile malformed publishing history records.")
        # Deletion of a recorded attempt must never silently erase evidence.
        if old is not sentinel and (ours is sentinel or theirs is sentinel):
            raise RuntimeError("Publishing history deletion requires manual reconciliation.")
        if ours == theirs:
            chosen = ours
        elif ours == old:
            chosen = theirs
        elif theirs == old:
            chosen = ours
        else:
            raise RuntimeError(
                f"Conflicting publishing history update for {key!r}; "
                "manual reconciliation required."
            )
        if chosen is not sentinel:
            merged[key] = chosen
    return merged


def _write_history_atomically(destination, content):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent,
        prefix=".history-", suffix=".tmp", delete=False,
    ) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        temp_path = temporary.name
    try:
        os.replace(temp_path, destination)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def save_history(history):
    history_checkout = Path("publishing-history")
    branch_file = history_checkout / HISTORY_FILE.name

    if not history_checkout.is_dir():
        raise RuntimeError("Publishing history checkout is missing.")

    # Save the exact checkout baseline to detect concurrent conflicting
    # modifications. We only reconcile disjoint fingerprint records.
    base = json.loads(branch_file.read_text(encoding="utf-8")) if branch_file.exists() else {}
    if not isinstance(base, dict):
        raise RuntimeError("Invalid publishing history checkout.")
    content = json.dumps(history, indent=2) + "\n"
    for destination in (HISTORY_FILE, branch_file):
        _write_history_atomically(destination, content)

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(history_checkout), *args],
            check=True, timeout=60,
        )

    def commit_if_changed():
        git("add", HISTORY_FILE.name)
        changes = subprocess.run(
            ["git", "-C", str(history_checkout), "diff", "--cached", "--quiet"],
            check=False, timeout=60,
        )
        if changes.returncode == 0:
            return False
        if changes.returncode != 1:
            raise RuntimeError("Could not inspect history changes.")
        git("commit", "-m", "Update Instagram publishing history")
        return True

    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com")
    if not commit_if_changed():
        return

    try:
        git("push", "origin", "HEAD:publishing-history")
    except subprocess.CalledProcessError:
        # Reconcile against a freshly fetched remote. The checkout is
        # dedicated to publishing-history; never force-push.
        for attempt in range(2):
            try:
                git("fetch", "origin", "publishing-history")
                result = subprocess.run(
                    ["git", "-C", str(history_checkout),
                     "show", f"FETCH_HEAD:{HISTORY_FILE.name}"],
                    check=True, timeout=60, text=True, capture_output=True,
                )
                remote = json.loads(result.stdout)
                merged = merge_history_updates(base, history, remote)
                git("reset", "--hard", "FETCH_HEAD")
                reconciled_content = json.dumps(merged, indent=2) + "\n"
                for destination in (HISTORY_FILE, branch_file):
                    _write_history_atomically(destination, reconciled_content)
                if not commit_if_changed():
                    history.clear()
                    history.update(merged)
                    return
                git("push", "origin", "HEAD:publishing-history")
                history.clear()
                history.update(merged)
                print("Publishing history reconciled and saved to GitHub.")
                return
            except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
                if attempt == 1:
                    raise RuntimeError(
                        "History synchronization failed after bounded retries. "
                        "Inspect the remote branch before publishing."
                    ) from error
        raise RuntimeError("Publishing history could not be synchronized.")
    print("Publishing history saved to GitHub.")


def approval_fingerprint(manifest, image_urls):
    """Bind approval to the exact images, order, alt text, sources and caption."""
    reviewed = {
        "image_urls": image_urls,
        "article_urls": manifest.get("article_urls", []),
        "caption": manifest.get("caption", ""),
        "first_comment": manifest.get("first_comment", ""),
        "slides": [
            {"slide": slide.get("slide"), "alt_text": slide.get("alt_text", "")}
            for slide in manifest.get("slides", [])
        ],
    }
    canonical = json.dumps(reviewed, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_manifest():
    if not MANIFEST_FILE.exists():
        raise RuntimeError("Instagram carousel manifest is missing.")

    data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    slides = data.get("slides", [])

    if len(slides) != CAROUSEL_SIZE:
        raise RuntimeError("Exactly seven slides are required.")

    urls = []

    for slide in slides:
        url = slide.get("image_url") or slide.get("secure_url")

        if not url or not url.startswith("https://"):
            raise RuntimeError("Invalid image URL.")

        if "res.cloudinary.com/" not in url:
            raise RuntimeError("Image must be hosted on Cloudinary.")

        urls.append(url)

    if len(set(urls)) != CAROUSEL_SIZE:
        raise RuntimeError("Duplicate images detected.")

    return data, urls


def api_request(method, endpoint, token, payload=None):
    response = requests.request(
        method,
        f"{API_BASE}/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        data=payload if method == "POST" else None,
        params=payload if method == "GET" else None,
        timeout=60,
    )

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            f"Instagram returned HTTP {response.status_code}"
        )

    if not response.ok or "error" in result:
        if response.status_code == 401:
            raise RuntimeError("Instagram authentication failed (401): check token expiry and rotate the production secret.")
        error = result.get("error", {})
        raise RuntimeError(
            f"Instagram API error: {error.get('message', 'Unknown error')}"
        )

    return result


def wait_for_container(container_id, token):
    for _ in range(20):
        result = api_request(
            "GET",
            container_id,
            token,
            {"fields": "status_code"},
        )

        status = result.get("status_code")

        if status == "FINISHED":
            return

        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Media processing failed: {status}")

        time.sleep(15)

    raise RuntimeError("Timed out waiting for media processing.")


def create_ready_carousel(account_id, token, image_urls, manifest, history, fingerprint, caption):
    """Prepare and verify media without calling media_publish."""
    child_ids = []

    for index, image_url in enumerate(image_urls, start=1):
        result = api_request(
            "POST",
            f"{account_id}/media",
            token,
            {
                "image_url": image_url,
                "is_carousel_item": "true",
                "alt_text": manifest["slides"][index - 1].get("alt_text", ""),
            },
        )
        child_ids.append(result["id"])
        print(f"Created carousel item {index}/{len(image_urls)}.")

    result = api_request(
        "POST",
        f"{account_id}/media",
        token,
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
        },
    )

    carousel_id = result["id"]

    history[fingerprint]["instagram_container_id"] = carousel_id
    save_history(history)

    print(f"Instagram carousel container recorded: {carousel_id}")

    wait_for_container(carousel_id, token)

    return carousel_id


def main():
    manifest, image_urls = load_manifest()
    history = load_history()
    
    article_urls = manifest.get("article_urls", [])

    if len(article_urls) != CAROUSEL_SIZE:
        raise RuntimeError(
            "Exactly seven article URLs are required."
        )

    normalized_urls = [
        normalize_article_url(url)
        for url in article_urls
    ]

    if len(set(normalized_urls)) != CAROUSEL_SIZE:
        raise RuntimeError(
            "Duplicate articles found in today's carousel."
        )

    previously_published = set()

    for record in history.values():
        if not isinstance(record, dict):
            raise RuntimeError("Invalid publishing history record.")

        if record.get("status") == "published":
            for url in record.get("article_urls", []):
                previously_published.add(
                    normalize_article_url(url)
                )

    repeated = set(normalized_urls) & previously_published

    fingerprint = hashlib.sha256(
        json.dumps(image_urls, sort_keys=True).encode()
    ).hexdigest()

    print("Validated seven unique Cloudinary image URLs.")

    if fingerprint in history:
        status = history[fingerprint].get("status")
        if status != "failed":
            print(f"Existing publishing record: {status}")
            print("Skipping to prevent duplicate publishing.")
            return
        if history[fingerprint].get("publish_attempted_at"):
            raise RuntimeError("Failed record includes a publish attempt; reconciliation required.")
        print("Retrying a confirmed pre-publication failure.")

    # Existing exact-fingerprint records are idempotent. Different image
    # packages still cannot re-use articles from earlier published posts.
    if repeated:
        raise RuntimeError(
            f"Publishing blocked: {len(repeated)} "
            "previously published article(s) detected."
        )

    today = datetime.now(
        ZoneInfo("America/Toronto")
    ).date().isoformat()

    for record in history.values():
        if not isinstance(record, dict):
            raise RuntimeError("Invalid publishing history record.")

        if record.get("toronto_date") == today:
            if record.get("status") in ("pending", "published"):
                print(
                    "A publishing attempt already exists "
                    "for today. Skipping."
                )
                return

    reviewed_fingerprint = approval_fingerprint(manifest, image_urls)
    print(f"REVIEW FINGERPRINT: {reviewed_fingerprint}")

    if not PUBLISH_ENABLED:
        print("DRY RUN: Instagram publishing is disabled.")
        print("No Instagram API publishing requests were made.")
        return

    # Explicit human approval applies to the exact seven-image package,
    # never merely to a date, workflow run, or reusable manifest flag.
    approved = os.getenv("INSTAGRAM_APPROVED_FINGERPRINT", "").strip()
    if not approved or approved != reviewed_fingerprint:
        print(f"REVIEW REQUIRED: carousel fingerprint {reviewed_fingerprint}")
        print("No Instagram API publishing requests were made.")
        return

    if manifest.get("publish_enabled") is not True:
        raise RuntimeError(
            "Live publishing blocked: carousel manifest is disabled."
        )

    if os.getenv("INSTAGRAM_PERSISTENCE_READY") != "true":
        raise RuntimeError(
            "Live publishing blocked: persistent history is not ready."
        )

    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_USER_ID")

    if not token or not account_id:
        raise RuntimeError("Instagram credentials are missing.")

    caption = manifest.get("caption", "").strip()

    if not caption:
        raise RuntimeError("Instagram caption is missing.")

    if manifest.get("automated_checks_passed") is not True:
        raise RuntimeError(
            "Publishing blocked: automated validation has not passed."
        )

    if len(caption) > 2200:
        raise RuntimeError(
            "Instagram caption exceeds 2,200 characters."
        )

    if not any(
        word in caption.lower()
        for word in ("source:", "sources:", "via:")
    ):
        raise RuntimeError(
            "Instagram caption must include source attribution."
        )

    first_comment = manifest.get("first_comment", "")
    if not isinstance(first_comment, str) or len(first_comment) > 1000:
        raise RuntimeError("Invalid first-comment text.")
    first_comment = first_comment.strip()
    if first_comment and not first_comment.startswith("#"):
        raise RuntimeError("First comment must begin with a hashtag.")

    print("Caption safety checks passed.")

    history[fingerprint] = {
        "status": "pending",
        "toronto_date": today,
        "created_at": int(time.time()),
        "article_urls": normalized_urls,
        "image_urls": image_urls,
        "instagram_container_id": None,
    }
    save_history(history)

    print("Publishing attempt recorded as pending.")

    try:
        carousel_id = create_ready_carousel(
            account_id, token, image_urls, manifest, history, fingerprint, caption
        )
    except Exception:
        history[fingerprint]["status"] = "failed"
        history[fingerprint]["failed_at"] = int(time.time())
        save_history(history)
        raise

    # Save an irreversible-call checkpoint; subsequent failures remain pending.
    history[fingerprint]["publish_attempted_at"] = int(time.time())
    save_history(history)

    published = api_request(
        "POST",
        f"{account_id}/media_publish",
        token,
        {"creation_id": carousel_id},
    )

    history[fingerprint].update({
        "status": "published",
        "toronto_date": today,
        "instagram_media_id": published["id"],
        "published_at": int(time.time()),
        "article_urls": normalized_urls,
    })
    save_history(history)

    print(f"Instagram carousel published: {published['id']}")

    if first_comment:
        # A failed or timed-out comments request may still have succeeded.
        # Save this checkpoint before the irreversible call. Never
        # automatically retry unknown comment outcomes.
        history[fingerprint]["first_comment_status"] = "pending"
        save_history(history)
        try:
            comment = api_request(
                "POST", f"{published['id']}/comments", token,
                {"message": first_comment},
            )
        except Exception as error:
            raise RuntimeError(
                "Carousel was published, but first-comment outcome is unknown. "
                "Inspect Instagram and reconcile the history; do NOT republish."
            ) from error
        history[fingerprint]["first_comment_status"] = "posted"
        history[fingerprint]["first_comment_id"] = comment["id"]
        save_history(history)
        print("First hashtag comment posted and recorded.")


if __name__ == "__main__":
    try:
        
        main()
    except Exception as error:
        print(f"Publishing stopped: {error}", file=sys.stderr)
        sys.exit(1)
