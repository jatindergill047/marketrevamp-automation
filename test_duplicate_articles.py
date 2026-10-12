import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import publish_instagram as publisher


def main():
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        manifest_path = folder / "manifest.json"
        history_path = folder / "history.json"

        manifest = json.loads(
            Path("instagram_carousel_manifest.json").read_text(
                encoding="utf-8"
            )
        )

        article_urls = manifest["article_urls"]

        history = {
            "simulated-previous-post": {
                "status": "published",
                "toronto_date": "2026-01-01",
                "article_urls": [article_urls[0]],
            }
        }

        manifest_path.write_text(json.dumps(manifest))
        history_path.write_text(json.dumps(history))

        with (
            patch.object(publisher, "MANIFEST_FILE", manifest_path),
            patch.object(publisher, "HISTORY_FILE", history_path),
            patch.object(publisher, "PUBLISH_ENABLED", False),
        ):
            try:
                publisher.main()
            except RuntimeError as error:
                if "previously published article" in str(error):
                    print("PASS: Duplicate article correctly blocked.")
                    return
                raise

        raise AssertionError(
            "FAIL: Duplicate article was not blocked."
        )


if __name__ == "__main__":
    main()
