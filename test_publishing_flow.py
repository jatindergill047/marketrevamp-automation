
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

        manifest = json.loads(
            Path("instagram_carousel_manifest.json").read_text(
                encoding="utf-8"
            )
        )

        # Enable publishing only inside this simulated test.
        manifest["publish_enabled"] = True
        manifest["automated_checks_passed"] = True

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
                },
            ),
        ):
            publisher.main()

        assert len(saved_history) == 3

        records = list(saved_history[-1].values())
        assert len(records) == 1

        record = records[0]

        assert record["status"] == "published"
        assert record["instagram_media_id"] == "TEST_PUBLISHED_POST"
        assert len(record["article_urls"]) == 5
        assert record["instagram_container_id"] == "TEST_CONTAINER_6"

        assert sum(
            1 for method, endpoint in calls
            if method == "POST" and endpoint.endswith("/media")
        ) == 6

        assert sum(
            1 for method, endpoint in calls
            if method == "POST" and endpoint.endswith("/media_publish")
        ) == 1

        print("PASS: Full publishing flow simulated successfully.")
        print("PASS: Five child containers and one carousel simulated.")
        print("PASS: Pending and published history recorded.")
        print("PASS: No real Instagram API requests were made.")


if __name__ == "__main__":
    main()
