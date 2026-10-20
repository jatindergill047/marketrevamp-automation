
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import publish_instagram as publisher


def main():
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)

        manifest_path = folder / "manifest.json"
        history_path = folder / "history.json"

        source_manifest = Path("instagram_carousel_manifest.json")
        if source_manifest.is_file():
            manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
        else:
            # PR CI has no generated production artifacts. Exercise the same
            # publisher with a complete offline-only seven-image fixture.
            manifest = {
                "slides": [
                    {"slide": i + 1,
                     "image_url": f"https://res.cloudinary.com/demo/image/upload/test{i + 1}.jpg",
                     "alt_text": f"Test article {i + 1}"}
                    for i in range(7)
                ],
                "article_urls": [f"https://example.com/article-{i + 1}"
                                 for i in range(7)],
                "caption": "Sources: example.com (offline simulation)",
            }

        # Enable publishing only inside this simulated test.
        manifest["publish_enabled"] = True
        manifest["automated_checks_passed"] = True
        manifest["caption"] += "\n\n#MarketRevamp #AI #Technology #Crypto #Bitcoin #StockMarket"
        manifest["first_comment"] = ""

        image_urls = [slide.get("image_url") or slide.get("secure_url")
                      for slide in manifest["slides"]]
        approval_fingerprint = publisher.approval_fingerprint(manifest, image_urls)

        manifest_path.write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        history_path.write_text(
            json.dumps({}), encoding="utf-8"
        )

        calls = []
        saved_history = []

        def fake_api(method, endpoint, token, payload=None):
            calls.append((method, endpoint))

            if method == "GET":
                return {"status_code": "FINISHED"}

            if endpoint.endswith("/media_publish"):
                return {"id": "TEST_PUBLISHED_POST"}

            if endpoint.endswith("/comments"):
                return {"id": "TEST_HASHTAG_COMMENT"}

            if endpoint.endswith("/media"):
                count = sum(
                    1 for m, e in calls
                    if m == "POST" and e.endswith("/media")
                )
                return {"id": f"TEST_CONTAINER_{count}"}

            raise AssertionError(
                f"Unexpected API request: {method} {endpoint}"
            )

        def fake_save(history):
            snapshot = json.loads(json.dumps(history))
            saved_history.append(snapshot)
            history_path.write_text(
                json.dumps(snapshot), encoding="utf-8"
            )

        with (
            patch.object(publisher, "MANIFEST_FILE", manifest_path),
            patch.object(publisher, "HISTORY_FILE", history_path),
            patch.object(publisher, "PUBLISH_ENABLED", True),
            patch.object(publisher, "api_request", fake_api),
            patch.object(publisher, "save_history", fake_save),
            patch.object(publisher, "wait_for_container", lambda *args: None),
            patch.dict(
                publisher.os.environ,
                {
                    "INSTAGRAM_PERSISTENCE_READY": "true",
                    "INSTAGRAM_ACCESS_TOKEN": "TEST_TOKEN",
                    "INSTAGRAM_USER_ID": "TEST_ACCOUNT",
                    "INSTAGRAM_APPROVED_FINGERPRINT": approval_fingerprint,
                },
            ),
        ):
            publisher.main()

        # With hashtags in the caption, the publisher needs only four
        # durable history checkpoints and never calls the comments API.
        assert len(saved_history) == 4, (
            f"Expected four persistence checkpoints, got {len(saved_history)}"
        )
        checkpoints = [next(iter(snapshot.values())) for snapshot in saved_history]
        assert [item["status"] for item in checkpoints] == [
            "pending", "pending", "pending", "published",
        ]
        assert "publish_attempted_at" not in checkpoints[1]
        assert "publish_attempted_at" in checkpoints[2]
        assert "first_comment_status" not in checkpoints[3]

        records = list(saved_history[-1].values())
        assert len(records) == 1

        record = records[0]

        assert record["status"] == "published"
        assert record["instagram_media_id"] == "TEST_PUBLISHED_POST"
        assert len(record["article_urls"]) == 7
        assert record["instagram_container_id"] == "TEST_CONTAINER_8"
        assert "first_comment_status" not in record
        assert "first_comment_id" not in record

        assert sum(
            1 for method, endpoint in calls
            if method == "POST" and endpoint.endswith("/media")
        ) == 8

        assert sum(
            1 for method, endpoint in calls
            if method == "POST" and endpoint.endswith("/media_publish")
        ) == 1

        print("PASS: Full publishing flow simulated successfully.")
        print("PASS: Seven child containers and one carousel simulated.")
        print("PASS: Pending and published history recorded.")
        assert sum(
            1 for method, endpoint in calls
            if method == "POST" and endpoint.endswith("/comments")
        ) == 0
        print("PASS: Hashtags travel in the caption; no comment API requests.")
        print("PASS: No real Instagram API requests were made.")


if __name__ == "__main__":
    main()
