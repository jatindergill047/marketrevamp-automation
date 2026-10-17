"""Offline history conflict reconciliation tests using local Git remotes."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_instagram as publisher


def git(where, *args):
    return subprocess.run(["git", "-C", str(where), *args],
                          check=True, capture_output=True, text=True)


class HistoryReconcileTests(unittest.TestCase):
    def test_disjoint_updates_merge_and_same_record_conflicts(self):
        base = {"original": {"status": "pending"}}
        ours = {**base, "ours": {"status": "pending"}}
        theirs = {**base, "theirs": {"status": "published"}}
        merged = publisher.merge_history_updates(base, ours, theirs)
        self.assertEqual(set(merged), {"original", "ours", "theirs"})
        with self.assertRaisesRegex(RuntimeError, "Conflicting"):
            publisher.merge_history_updates(
                base, {"original": {"status": "published"}},
                {"original": {"status": "failed"}},
            )
        with self.assertRaisesRegex(RuntimeError, "deletion"):
            publisher.merge_history_updates(base, {}, base)

    def test_stale_push_reconciles_disjoint_keys_without_force_push(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "remote.git"
            local = root / "publishing-history"
            other = root / "other"
            subprocess.run(["git", "init", "--bare", str(origin)],
                           check=True, capture_output=True)
            subprocess.run(["git", "clone", str(origin), str(local)],
                           check=True, capture_output=True)
            git(local, "checkout", "-b", "publishing-history")
            git(local, "config", "user.name", "Test")
            git(local, "config", "user.email", "test@example.com")
            (local / "instagram_publish_history.json").write_text("{}\n")
            git(local, "add", ".")
            git(local, "commit", "-m", "initial")
            git(local, "push", "-u", "origin", "publishing-history")
            subprocess.run(["git", "clone", "-b", "publishing-history",
                            str(origin), str(other)],
                           check=True, capture_output=True)
            git(other, "config", "user.name", "Test")
            git(other, "config", "user.email", "test@example.com")
            (other / "instagram_publish_history.json").write_text(
                json.dumps({"remote": {"status": "published"}}) + "\n")
            git(other, "add", ".")
            git(other, "commit", "-m", "remote update")
            git(other, "push")
            history = {"local": {"status": "pending"}}
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.object(publisher, "HISTORY_FILE",
                                  Path("instagram_publish_history.json")):
                    publisher.save_history(history)
            finally:
                os.chdir(original_cwd)
            reconciled = json.loads(
                (local / "instagram_publish_history.json").read_text())
            self.assertEqual(set(reconciled), {"local", "remote"})
            self.assertEqual(reconciled, history)
            git(other, "pull", "--ff-only")
            self.assertEqual(json.loads(
                (other / "instagram_publish_history.json").read_text()),
                reconciled)


if __name__ == "__main__":
    unittest.main()
