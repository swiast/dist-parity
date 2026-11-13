"""Self-contained synthetic sdist/wheel demonstration.

This is a maintainer-authored example, NOT independent package adoption.
No network, installation, execution of wheel contents, or private data.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import tarfile
import zipfile

from dist_parity.core import compare


def write_sdist(path: Path) -> None:
    data = {
        "example_pkg-1.0.0/PKG-INFO": (
            b"Metadata-Version: 2.4\n"
            b"Name: example-pkg\n"
            b"Version: 1.0.0\n"
            b"Requires-Python: >=3.11\n\n"
        ),
        "example_pkg-1.0.0/pyproject.toml": (
            b"[build-system]\nrequires = []\n"
            b"build-backend = 'example_backend'\n"
        ),
    }
    with tarfile.open(path, mode="w:gz") as archive:
        for name, content in data.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, BytesIO(content))


def write_wheel(path: Path) -> None:
    base = "example_pkg-1.0.0.dist-info/"
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr(
            base + "METADATA",
            "Metadata-Version: 2.4\n"
            "Name: example-pkg\n"
            "Version: 1.0.0\n"
            "Requires-Python: >=3.12\n\n",
        )
        archive.writestr(base + "WHEEL", "Wheel-Version: 1.0\nGenerator: synthetic-example\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr(base + "RECORD", "")


def main() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        sdist = root / "example_pkg-1.0.0.tar.gz"
        wheel = root / "example_pkg-1.0.0-py3-none-any.whl"
        write_sdist(sdist)
        write_wheel(wheel)
        report = compare(sdist, wheel)
        findings = [(finding.code, finding.field) for finding in report.findings]
        assert not report.ok, "The intentionally inconsistent example should fail"
        assert ("FIELD_MISMATCH", "requires-python") in findings, findings
        print("EXPECTED MISMATCH: source Requires-Python >=3.11, wheel >=3.12")
        print("RESULT: dist-parity detected non-Dynamic Requires-Python change")
        print("PASS: synthetic mismatch was correctly detected")


if __name__ == "__main__":
    main()
