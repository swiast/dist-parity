"""Repo-scoped publication-permission regression checks.

These offline tests do not parse arbitrary YAML. They protect the exact
maintainer-controlled workflow files against accidental release triggers or
write-token permissions during normal source CI. A future intentionally
authorized publishing change requires human review and updated policy tests.
"""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class ReleasePermissionTests(unittest.TestCase):
    def test_regular_ci_has_only_read_permissions_and_no_release_job(self):
        workflow = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("  pull_request:", workflow)
        self.assertIn("  push:", workflow)
        self.assertNotIn("\n  release:\n", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release upload", workflow)

    def test_pypi_publisher_is_manual_and_environment_gated(self):
        workflow = (WORKFLOWS / "pypi-publish.yml").read_text(encoding="utf-8")
        self.assertIn("on:\n  workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  pull_request:", workflow)
        self.assertNotIn("\n  release:", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("environment: pypi", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("sha256sum --check --strict", workflow)

    def test_nonpublishing_preflight_never_requests_publisher_permissions(self):
        workflow = (WORKFLOWS / "release-preflight.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("pypa/gh-action-pypi-publish", workflow)

    def test_no_other_workflow_contains_publishing_operations(self):
        for path in WORKFLOWS.glob("*.yml"):
            if path.name == "pypi-publish.yml":
                continue
            with self.subTest(workflow=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("gh release create", source)
                self.assertNotIn("gh release upload", source)
                self.assertNotIn("pypa/gh-action-pypi-publish", source)
                self.assertNotIn("contents: write", source)


if __name__ == "__main__":
    unittest.main()
