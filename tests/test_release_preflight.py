"""Offline, synthetic tests for the non-publishing release-candidate receipt."""
from __future__ import annotations

import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from scripts.release_preflight import build_receipt, main
from test_core import make_pair


class ReleasePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def test_success_receipt_contains_exact_artifact_hashes(self):
        sdist, wheel = make_pair(self.directory)
        status, receipt = build_receipt(self.directory)
        self.assertEqual(status, 0)
        self.assertEqual(receipt["status"], "pass")
        self.assertTrue(receipt["ok"])
        self.assertFalse(receipt["provenance_verified"])
        self.assertEqual(receipt["purpose"], "unpublished-release-candidate-preflight")
        for key, file in (("sdist", sdist), ("wheel", wheel)):
            self.assertEqual(receipt["artifacts"][key]["filename"], file.name)
            self.assertEqual(receipt["artifacts"][key]["size_bytes"], file.stat().st_size)
            self.assertEqual(
                receipt["artifacts"][key]["sha256"],
                hashlib.sha256(file.read_bytes()).hexdigest(),
            )

    def test_mismatch_returns_exit_one_without_publishing(self):
        make_pair(self.directory, wdict={"Summary": "wheel-only"})
        code, result = build_receipt(self.directory)
        self.assertEqual(code, 1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "mismatch")
        self.assertIn("FIELD_MISMATCH", [f["code"] for f in result["report"]["findings"]])

    def test_missing_or_ambiguous_pair_returns_exit_two(self):
        status, receipt = build_receipt(self.directory)
        self.assertEqual(status, 2)
        self.assertEqual(receipt["status"], "input_error")
        self.assertIn("expected exactly one", receipt["error"])
        make_pair(self.directory)
        (self.directory / "extra-1.0-py3-none-any.whl").write_bytes(b"junk")
        status, receipt = build_receipt(self.directory)
        self.assertEqual(status, 2)
        self.assertIn("expected exactly one", receipt["error"])

    def test_explicit_json_file_and_stdout_match(self):
        make_pair(self.directory)
        output = self.directory / "receipt.json"
        captured = io.StringIO()
        with redirect_stdout(captured):
            status = main(["--dist-dir", str(self.directory), "--output", str(output)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), json.loads(captured.getvalue()))
        self.assertEqual(json.loads(captured.getvalue())["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
