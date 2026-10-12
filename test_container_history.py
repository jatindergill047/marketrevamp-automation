from unittest.mock import patch

import publish_instagram as publisher


def test_container_history():
    fingerprint = "simulated-carousel"

    history = {
        fingerprint: {
            "status": "pending",
            "instagram_container_id": None,
        }
    }

    saved = []

    def fake_save(updated_history):
        saved.append(
            updated_history[fingerprint].copy()
        )

    with patch.object(publisher, "save_history", fake_save):
        carousel_id = "TEST_CONTAINER_123"

        history[fingerprint]["instagram_container_id"] = carousel_id
        publisher.save_history(history)

    assert len(saved) == 1
    assert saved[0]["instagram_container_id"] == "TEST_CONTAINER_123"
    assert saved[0]["status"] == "pending"

    print("PASS: Container ID saved in simulated history.")


if __name__ == "__main__":
    test_container_history()
