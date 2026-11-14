"""Offline tests for the optional public-package reproducer (no PyPI calls)."""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "reproduce_flit_case.py"


class ReproductionSafetyTests(unittest.TestCase):
    def invoke(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *arguments],
                              capture_output=True, text=True, timeout=30)

    def test_offline_self_test(self):
        result = self.invoke("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OFFLINE SELF-TEST PASS", result.stdout)
        self.assertIn("NOT an independent build reproduction", result.stdout)

    def test_dry_run_names_pinned_py_pi_artifacts(self):
        result = self.invoke("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NO NETWORK / NO THIRD-PARTY CODE EXECUTED", result.stdout)
        for release in ("packaging-25.0.tar.gz", "flit_core==3.12.0",
                        "flit_core==4.2.0", "wheel==0.48.0"):
            self.assertIn(release, result.stdout)
        self.assertIn("d443872c98d677bf60f6a1f2f8c1cb748e8fe762d2bf9d3148b5599295b0fc4f",
                      result.stdout)

    def test_requires_opt_in_flag(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertIn("required", result.stderr)


if __name__ == "__main__":
    unittest.main()
