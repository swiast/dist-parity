#!/usr/bin/env python3
"""Optional, hash-pinned reproduction of a public Python packaging experiment.

No network and no third-party code execution in --dry-run or --self-test.
--execute downloads PyPI artifacts, verifies published SHA-256 digests,
installs known wheels in a disposable virtualenv, and runs Flit build backends.

This is MAINTAINER evidence, never proof of independent use or a standards bug.
Requires Python 3.13 for --execute. Do not run on a system you do not trust.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.request import urlopen

# Exact published PyPI release artifacts; source: the "Release files" pages.
# Hashes are integrity pins, not a security audit or signature verification.
SDIST_URL = (
    "https://files.pythonhosted.org/packages/a1/d4/"
    "1fc4078c65507b51b96ca8f8c3ba19e6a61c8253c72794544580a7b6c24d/"
    "packaging-25.0.tar.gz"
)
SDIST_NAME = "packaging-25.0.tar.gz"
SDIST_HASH = "d443872c98d677bf60f6a1f2f8c1cb748e8fe762d2bf9d3148b5599295b0fc4f"
WHEELS = {
    "flit_core==3.12.0": (
        "flit_core-3.12.0-py3-none-any.whl",
        "e7a0304069ea895172e3c7bb703292e992c5d1555dd1233ab7b5621b5b69e62c",
    ),
    "flit_core==4.2.0": (
        "flit_core-4.2.0-py3-none-any.whl",
        "2bee22dc8ba89c2e35b4e1ad575e596aac945c85672dd8f3cad21b629036e044",
    ),
    "wheel==0.48.0": (
        "wheel-0.48.0-py3-none-any.whl",
        "3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab",
    ),
}
EXPECTED = {
    "sdist": ("2.4", []),
    "flit_core_3.12.0": ("2.4", []),
    "flit_core_4.2.0": ("2.5", ["packaging"]),
}
MAX_FILE_BYTES = 5_000_000
MAX_METADATA_BYTES = 2_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while data := f.read(128 * 1024):
            digest.update(data)
    return digest.hexdigest()


def verify_hash(path: Path, expected: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Expected hash must be 64 lowercase hexadecimal characters")
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"Artifact exceeds {MAX_FILE_BYTES} bytes: {path.name}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"SHA-256 MISMATCH for {path.name}: expected {expected}, got {actual}")
    return actual


def fetch_sdist(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(SDIST_URL, timeout=40) as response, dest.open("wb") as output:
        transferred = 0
        while piece := response.read(128 * 1024):
            transferred += len(piece)
            if transferred > MAX_FILE_BYTES:
                raise ValueError("Source download exceeds declared safety limit")
            output.write(piece)
    verify_hash(dest, SDIST_HASH)
    return dest


def run(command: list[str], label: str) -> None:
    print(f"\n== {label} ==", flush=True)
    subprocess.run(command, check=True)  # No shell expansion, no other repository writes.


def download_wheels(python: Path, vendor: Path) -> dict[str, Path]:
    vendor.mkdir(parents=True, exist_ok=True)
    resolved = {}
    for spec, (filename, digest) in WHEELS.items():
        run([str(python), "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
             "--dest", str(vendor), spec], f"download verified backend wheel: {spec}")
        artifact = vendor / filename
        verify_hash(artifact, digest)  # Must pass before installing wheels.
        resolved[spec] = artifact
    return resolved


def fields(data: bytes) -> dict[str, object]:
    if len(data) > MAX_METADATA_BYTES:
        raise ValueError("Metadata exceeds size limit")
    message = BytesParser(policy=policy.compat32).parsebytes(data)
    if message.defects:
        raise ValueError(f"Invalid Core Metadata header format: {message.defects!r}")
    return {
        "Metadata-Version": message.get("Metadata-Version"),
        "Name": message.get("Name"),
        "Version": message.get("Version"),
        "Dynamic": message.get_all("Dynamic", []),
        "Import-Name": message.get_all("Import-Name", []),
        "Import-Namespace": message.get_all("Import-Namespace", []),
    }


def from_sdist(path: Path) -> dict[str, object]:
    with tarfile.open(path, mode="r:gz") as archive:
        member = archive.getmember("packaging-25.0/PKG-INFO")
        if not member.isfile() or member.size > MAX_METADATA_BYTES:
            raise ValueError("Missing/oversized source PKG-INFO")
        source = archive.extractfile(member)
        if source is None:
            raise ValueError("Source PKG-INFO unreadable")
        return fields(source.read(MAX_METADATA_BYTES + 1))


def from_wheel(directory: Path) -> dict[str, object]:
    wheels = list(directory.glob("packaging-25.0-*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"Expected exactly one packaging 25.0 wheel in {directory}, found {len(wheels)}")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError(f"Expected exactly one wheel METADATA, got {names!r}")
        entry = archive.getinfo(names[0])
        if entry.file_size > MAX_METADATA_BYTES:
            raise ValueError("Wheel metadata exceeds size limit")
        with archive.open(entry) as stream:
            return fields(stream.read(MAX_METADATA_BYTES + 1))


def validate_headers(record: dict[str, dict[str, object]]) -> None:
    for name, (version, import_names) in EXPECTED.items():
        meta = record[name]
        if (meta["Metadata-Version"], meta["Import-Name"]) != (version, import_names):
            raise AssertionError(f"{name}: expected {(version, import_names)}, got {meta}")
        if meta["Name"] != "packaging" or meta["Version"] != "25.0":
            raise AssertionError(f"{name}: unexpected package identity: {meta}")
        if meta["Dynamic"]:
            raise AssertionError(f"{name}: Dynamic headers unexpectedly present: {meta}")


def self_test() -> None:
    """Test parsing/hash guards using solely synthetic bytes, with no network."""
    with tempfile.TemporaryDirectory(prefix="dist-parity-offline-selftest-") as temp:
        root = Path(temp)
        raw = b"test integrity bytes"
        artifact = root / "synthetic.bin"
        artifact.write_bytes(raw)
        good = hashlib.sha256(raw).hexdigest()
        assert verify_hash(artifact, good) == good
        artifact.write_bytes(raw + b" altered")
        try:
            verify_hash(artifact, good)
        except ValueError as exc:
            assert "MISMATCH" in str(exc)
        else:
            raise AssertionError("Tampered bytes were accepted")

        def meta(version: str, extra: str = "") -> bytes:
            return (f"Metadata-Version: {version}\nName: packaging\nVersion: 25.0\n{extra}\n").encode()

        source = root / SDIST_NAME
        with tarfile.open(source, "w:gz") as tar:
            data = meta("2.4")
            info = tarfile.TarInfo("packaging-25.0/PKG-INFO")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        def wheel(label: str, data: bytes) -> Path:
            directory = root / label
            directory.mkdir()
            with zipfile.ZipFile(directory / "packaging-25.0-py3-none-any.whl", "w") as zipout:
                zipout.writestr("packaging-25.0.dist-info/METADATA", data)
            return directory

        record = {
            "sdist": from_sdist(source),
            "flit_core_3.12.0": from_wheel(wheel("old", meta("2.4"))),
            "flit_core_4.2.0": from_wheel(wheel("new", meta("2.5", "Import-Name: packaging\n"))),
        }
        validate_headers(record)
    print("OFFLINE SELF-TEST PASS: hash guard rejects alteration and header parser reads synthetic records")
    print("NOT an independent build reproduction, package download or third-party adoption")


def execute() -> None:
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("--execute requires Python 3.13 to match the pinned CI interpreter")
    with tempfile.TemporaryDirectory(prefix="dist-parity-flit-verified-") as temp:
        root = Path(temp)
        env = root / "venv"
        venv.EnvBuilder(with_pip=True).create(env)
        python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        # Direct raw download does not invoke packaging's build backend before hash check.
        source = fetch_sdist(root / "source" / SDIST_NAME)
        wheel_paths = download_wheels(python, root / "vendor")
        results = {"sdist": from_sdist(source)}
        for version in ("3.12.0", "4.2.0"):
            run([str(python), "-m", "pip", "install", "--no-index", "--no-deps",
                 "--force-reinstall", str(wheel_paths[f"flit_core=={version}"]),
                 str(wheel_paths["wheel==0.48.0"])], f"install verified flit_core {version}")
            # Check that pip did not silently install another backend version.
            run([str(python), "-c",
                 "from importlib.metadata import version; "
                 f"assert version('flit_core') == '{version}'; "
                 "assert version('wheel') == '0.48.0'"], "check installed backend versions")
            target = root / f"flit{version.replace('.', '')}"
            target.mkdir()
            run([str(python), "-m", "pip", "wheel", "--no-index", "--no-deps",
                 "--no-build-isolation", "--wheel-dir", str(target), str(source)],
                f"build wheel with flit_core {version}")
            results[f"flit_core_{version}"] = from_wheel(target)
        validate_headers(results)
        receipt = {
            "case": "packaging 25.0 sdist built with pinned Flit backends",
            "python": sys.version.split()[0],
            "sdist_sha256": sha256(source),
            "pinned_download_hashes": {"source": SDIST_HASH, **{name: info[1] for name, info in WHEELS.items()}},
            "headers": results,
            "note": "Maintainer-operated reproduction; NOT proof of a standards violation or independent adoption",
        }
        print("\nREPRODUCTION PASS — PUBLISHED PYPI FILE HASHES VERIFIED")
        print(json.dumps(receipt, indent=2))
        print("Disposably built archives and virtual environment will be removed")


def dry_run() -> None:
    print("NO NETWORK / NO THIRD-PARTY CODE EXECUTED")
    print(f"Direct HTTPS source: {SDIST_URL}\nSHA-256: {SDIST_HASH}")
    for spec, (file, digest) in WHEELS.items():
        print(f"  pinned wheel {spec}: {file} SHA-256={digest}")
    print("After verifying all downloaded file hashes, create disposable Python 3.13 venv;")
    print("install verified wheels with pip --no-index --no-deps, build two wheels from exact sdist,")
    print("then assert Metadata-Version and Import-Name headers and print a public evidence receipt.")
    print("--execute intentionally runs third-party Flit build code; only use trusted disposable environments.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print operations and fixed hashes; no network")
    mode.add_argument("--self-test", action="store_true", help="Synthetic parser/hash tests only; no network")
    mode.add_argument("--execute", action="store_true", help="Download pinned PyPI files, execute backend in disposable venv")
    args = parser.parse_args()
    if args.dry_run:
        dry_run()
    elif args.self_test:
        self_test()
    else:
        execute()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
