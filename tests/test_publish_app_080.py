#!/usr/bin/env python3
"""Fail-closed controls for this one accepted release; no network or publishing."""
import importlib.util
import io
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

spec = importlib.util.spec_from_file_location("promotion", Path(__file__).resolve().parents[1] / "scripts/publish_app_080.py")
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)


class PromotionControls(unittest.TestCase):
    def test_wrong_repository_refuses_before_client_creation(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "wrong/repo", "GITHUB_REF": "refs/heads/release/app-0.8.0"}), \
             patch.object(promotion, "GitHub") as client:
            with self.assertRaisesRegex(ValueError, "Wrong publication"):
                promotion.publish(types.SimpleNamespace())
            client.assert_not_called()

    def test_existing_tag_refuses_before_any_mutation(self):
        requests = []
        class Client:
            def __init__(self, token):
                pass
            def api(self, path, method="GET", **kwargs):
                requests.append((path, method))
                return {"ref": "refs/tags/" + promotion.TAG}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": promotion.REPOSITORY,
                                     "GITHUB_REF": "refs/heads/release/app-0.8.0", "GITHUB_SHA": promotion.SOURCE}), \
             patch.object(promotion, "GitHub", Client), patch.object(Path, "read_text", return_value="0.8.0 " + "notes " * 100):
            with self.assertRaisesRegex(ValueError, "already exists"):
                promotion.publish(types.SimpleNamespace(publish_sha=promotion.SOURCE))
        self.assertEqual(requests, [("/git/ref/tags/" + promotion.TAG, "GET")])

    def test_skipped_job_step_refuses(self):
        class Client:
            def api(self, path):
                if "/jobs" not in path:
                    return {"head_sha": promotion.SOURCE, "status": "completed", "conclusion": "success"}
                return {"total_count": 5, "jobs": [{"name": name, "conclusion": "success", "steps": [
                    {"conclusion": "skipped" if name == "native-scroll-frames" else "success"}]} for name in promotion.JOBS]}
        with self.assertRaisesRegex(ValueError, "failed or skipped"):
            promotion.verify_run(Client())

    def test_different_packaged_identity_refuses(self):
        report = {"success": True, "nativeWindowsExecuted": True, "passed": 32, "skips": [],
                  "sourceCommit": promotion.SOURCE, "assetSha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "different application bytes"):
            promotion.check_report(report, 32)

    def test_zip_traversal_refuses(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as archive:
            archive.writestr("../escape", "untrusted")
        with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
            promotion.checked_zip(raw.getvalue())

    def test_api_redirect_refuses_without_forwarding_credentials(self):
        with patch.object(promotion.urllib.request, "build_opener") as opener, \
             patch.object(promotion.urllib.request, "urlopen") as default_open:
            opener.return_value.open.side_effect = urllib.error.HTTPError(
                "https://api.github.com/example", 302, "redirect", {"Location": "https://outside.invalid"}, None)
            with self.assertRaisesRegex(RuntimeError, "HTTP 302"):
                promotion.GitHub("dummy-token").api("/releases")
            opener.assert_called_once_with(promotion.NoRedirect)
            default_open.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
