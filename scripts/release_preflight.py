"""Non-publishing, read-only release-candidate receipt.

Build an sdist and wheel first (normally with 'python -m build'). This utility
checks the exact pair and records their digests; it does not prove provenance,
upload artifacts, create tags, or publish a package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from dist_parity import __version__
from dist_parity.core import ArtifactError, compare, locate_distributions

SCHEMA_VERSION = 1
CHUNK_SIZE = 1024 * 1024


def _artifact_info(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"filename": path.name, "size_bytes": size, "sha256": digest.hexdigest()}


def build_receipt(dist_dir: Path) -> tuple[int, dict]:
    """Return CLI-compatible exit code and an inspectable receipt."""
    receipt: dict = {
        "schema_version": SCHEMA_VERSION,
        "tool": "dist-parity",
        "checker_version": __version__,
        "purpose": "unpublished-release-candidate-preflight",
        "provenance_verified": False,
        "status": "input_error",
        "ok": False,
        "artifacts": {},
    }
    try:
        sdist, wheel = locate_distributions(dist_dir)
        receipt["artifacts"] = {
            "sdist": _artifact_info(sdist),
            "wheel": _artifact_info(wheel),
        }
        report = compare(sdist, wheel)
    except (ArtifactError, OSError) as exc:
        receipt["error"] = str(exc)
        return 2, receipt

    receipt["report"] = report.to_dict()
    receipt["ok"] = report.ok
    receipt["status"] = "pass" if report.ok else "mismatch"
    return (0 if report.ok else 1), receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify one built sdist/wheel pair and record SHA-256 hashes; NEVER publishes."
    )
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, help="optional local JSON receipt destination")
    args = parser.parse_args(argv)
    code, receipt = build_receipt(args.dist_dir)
    serialized = json.dumps(receipt, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
