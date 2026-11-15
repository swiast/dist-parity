"""Validate the public JSON report schema against actual CLI output.

This is an OPTIONAL developer/CI check, not a runtime dependency.
Install jsonschema==4.26.0 only in the isolated validation job.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from jsonschema import Draft202012Validator, ValidationError  # noqa: E402
from dist_parity.cli import main  # noqa: E402
from test_core import make_pair  # noqa: E402


def cli_json(argv: list[str]) -> tuple[int, dict]:
    output = StringIO()
    with redirect_stdout(output):
        code = main(argv)
    return code, json.loads(output.getvalue())


def run() -> None:
    schema_path = ROOT / "schemas" / "report-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        passing = root / "passing"
        passing.mkdir()
        make_pair(passing)
        success_code, good = cli_json(["--json", "--dist-dir", str(passing)])
        assert success_code == 0 and good["ok"] is True, good
        assert any(f["severity"] == "info" and f["code"] == "PARITY_OK" for f in good["findings"]), good

        failing = root / "failing"
        failing.mkdir()
        make_pair(failing, wdict={"Summary": "synthetic-regression"})
        failure_code, mismatch = cli_json(["--dist-dir", str(failing), "--json"])
        assert failure_code == 1 and mismatch["ok"] is False, mismatch

        missing_code, error = cli_json(["--json", "--dist-dir", str(root / "absent")])
        assert missing_code == 2 and error["ok"] is False, error

        argument_code, argument_error = cli_json(["--sdist", str(root / "missing.tar.gz"), "--json"])
        assert argument_code == 2 and argument_error["ok"] is False, argument_error

    for item in (good, mismatch, error, argument_error):
        validator.validate(item)

    bad_missing_required = deepcopy(good)
    del bad_missing_required["ok"]
    bad_extra_property = {**good, "unexpected": 1}
    bad_severity = deepcopy(mismatch)
    bad_severity["findings"][0]["severity"] = "fatal"
    bad_input_ok = {**error, "ok": True}
    bad_error_findings = {**error, "findings": [{"code": "x"}]}
    bad_error_extra = {**error, "sdist": "fake.tar.gz"}
    for label, item in (
        ("missing required key", bad_missing_required),
        ("unexpected property", bad_extra_property),
        ("unsupported severity", bad_severity),
        ("invalid input marked ok", bad_input_ok),
        ("input error with findings", bad_error_findings),
        ("unexpected input-error property", bad_error_extra),
    ):
        try:
            validator.validate(item)
        except ValidationError:
            continue
        raise AssertionError(f"schema accepted a negative control: {label}")

    print("PASS: schema valid; 4 real CLI outputs valid; 6 negative schema controls rejected")


if __name__ == "__main__":
    run()
