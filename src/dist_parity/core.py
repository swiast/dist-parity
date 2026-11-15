"""Read-only sdist/wheel metadata parity checks (PEP 643 / Core Metadata)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile
import zlib

MAX_METADATA_BYTES = 2_000_000
SUPPORTED_METADATA_MAJOR = 2
MAX_SUPPORTED_METADATA_MINOR = 6
MAX_ARCHIVE_MEMBERS = 50_000
MULTIPLE_USE_FIELDS = frozenset({
    "classifier", "platform", "supported-platform", "requires-dist",
    "provides-extra", "requires-external", "project-url", "license-file",
    "import-name", "import-namespace", "dynamic", "obsoletes-dist",
    "provides-dist", "obsoletes", "provides", "requires",
})
EXCLUDED_METADATA_FIELDS = frozenset({"metadata-version", "dynamic"})
# Core Metadata 2.6 (PEP 808) also protects the existing elements of
# these single-header, comma-separated lists when they are Dynamic.
CSV_DYNAMIC_FIELDS = frozenset({"keywords", "author-email", "maintainer-email"})


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Report:
    sdist: str
    wheel: str
    project: str | None
    version: str | None
    findings: list[Finding]

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "sdist": self.sdist, "wheel": self.wheel,
            "project": self.project, "version": self.version,
            "ok": self.ok, "findings": [f.to_dict() for f in self.findings],
        }


class ArtifactError(ValueError):
    """Invalid, missing, ambiguous, or unsupported distribution archive."""


def _identity_from_stem(stem: str, kind: str) -> tuple[str, str]:
    """Read the distribution name and version from an artifact component."""
    if "-" not in stem:
        raise ArtifactError(f"{kind}: expected normalized distribution-version name")
    name, version = stem.rsplit("-", 1)
    if not name or not version:
        raise ArtifactError(f"{kind}: missing distribution name or version")
    return name, version


def _obvious_version_conflict(candidate: str, metadata_version: str) -> bool:
    """Reject provable release-version conflicts without guessing PEP 440 aliases.

    Numeric-only versions have unambiguous release segments; trailing zero
    segments are equivalent (1.0 and 1.0.0). Complex PEP 440 spellings require
    an external normalizer, so this focused, dependency-free check defers them.
    """
    numeric = r"[0-9]+(?:\.[0-9]+)*"
    if not (re.fullmatch(numeric, candidate) and re.fullmatch(numeric, metadata_version)):
        return False

    def release(value: str) -> tuple[str, ...]:
        # Compare normalized decimal segments as strings: int() can raise
        # ValueError on untrusted, very long numeric version components.
        parts = [part.lstrip("0") or "0" for part in value.split(".")]
        while len(parts) > 1 and parts[-1] == "0":
            parts.pop()
        return tuple(parts)

    return release(candidate) != release(metadata_version)


def _name_matches_metadata(candidate: str, name: str) -> bool:
    return _normalize_name(candidate) == _normalize_name(name)


def _valid_archive_path(name: str) -> bool:
    p = PurePosixPath(name)
    return (
        bool(name) and not name.startswith("/") and "\\" not in name
        and not any(part in {"", ".", ".."} for part in name.split("/"))
        and not p.is_absolute() and not re.match(r"^[a-zA-Z]:", name)
    )


def _decode_metadata(data: bytes, context: str) -> dict[str, list[str]]:
    if len(data) > MAX_METADATA_BYTES:
        raise ArtifactError(f"{context}: metadata exceeds size limit")
    try:
        message = BytesParser(policy=policy.compat32).parsebytes(data)
    except Exception as exc:
        raise ArtifactError(f"{context}: could not parse metadata: {exc}") from exc
    if message.defects:
        raise ArtifactError(f"{context}: malformed metadata headers: {message.defects!r}")
    result: dict[str, list[str]] = {}
    for key in dict.fromkeys(k.lower() for k in message.keys()):
        result[key] = [str(v) for v in message.get_all(key, [])]
    for field in ("metadata-version", "name", "version"):
        if len(result.get(field, [])) != 1 or not result[field][0].strip():
            raise ArtifactError(f"{context}: expected exactly one nonempty {field!r} field")
    for field, values in result.items():
        if field not in MULTIPLE_USE_FIELDS and len(values) > 1:
            raise ArtifactError(f"{context}: repeated single-use field {field!r}")
    # Since Core Metadata 2.1, Description may be represented after the
    # blank line instead of as an email header. Treat both as the *same*
    # logical field for PEP 643 parity, normalizing CRLF line endings.
    if "description" in result:
        value = result["description"][0].replace("\r\n", "\n")
        result["description"] = [value.replace("\n       |", "\n")]
    payload = message.get_payload(decode=True)
    if payload:
        try:
            body = payload.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError as exc:
            raise ArtifactError(f"{context}: Description body must be UTF-8") from exc
        if "description" in result:
            raise ArtifactError(f"{context}: Description given in both header and body")
        result["description"] = [body]
    return result


def _sdist_metadata(path: Path) -> dict[str, list[str]]:
    if not path.is_file() or not path.name.endswith(".tar.gz"):
        raise ArtifactError(f"expected .tar.gz sdist: {path}")
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            files = []
            for member in archive:
                files.append(member)
                if len(files) > MAX_ARCHIVE_MEMBERS:
                    raise ArtifactError("sdist exceeds archive entry limit")
            names = [m.name for m in files]
            if len(names) != len(set(names)):
                raise ArtifactError("sdist contains duplicate archive entries")
            unsafe = [m.name for m in files if not _valid_archive_path(m.name.rstrip("/"))]
            if unsafe:
                raise ArtifactError(f"sdist has unsafe entry path: {unsafe[0]!r}")
            roots = {m.name.split("/")[0] for m in files}
            if len(roots) != 1:
                raise ArtifactError("sdist must contain exactly one top-level directory")
            root = next(iter(roots))
            meta_name = f"{root}/PKG-INFO"
            required_names = {meta_name, f"{root}/pyproject.toml"}
            by_name = {m.name: m for m in files}
            if not all(x in by_name and by_name[x].isfile() for x in required_names):
                raise ArtifactError("sdist must include root PKG-INFO and pyproject.toml")
            info = by_name[meta_name]
            if info.size > MAX_METADATA_BYTES:
                raise ArtifactError("sdist: PKG-INFO exceeds metadata size limit")
            stream = archive.extractfile(info)
            if stream is None:
                raise ArtifactError("sdist: PKG-INFO is unreadable")
            metadata = _decode_metadata(stream.read(MAX_METADATA_BYTES + 1), meta_name)
            expected = metadata["name"][0]
            file_name, file_version = _identity_from_stem(path.name[:-7], "sdist filename")
            root_name, root_version = _identity_from_stem(root, "sdist root directory")
            if not _name_matches_metadata(file_name, expected):
                raise ArtifactError("sdist filename distribution name differs from PKG-INFO Name")
            if not _name_matches_metadata(root_name, expected):
                raise ArtifactError("sdist root directory distribution name differs from PKG-INFO Name")
            version = metadata["version"][0]
            if _obvious_version_conflict(file_version, version):
                raise ArtifactError("sdist filename distribution version differs from PKG-INFO Version")
            if _obvious_version_conflict(root_version, version):
                raise ArtifactError("sdist root directory distribution version differs from PKG-INFO Version")
            return metadata
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise ArtifactError(f"could not read sdist {path}: {exc}") from exc


def _wheel_metadata(path: Path) -> dict[str, list[str]]:
    if not path.is_file() or path.suffix != ".whl":
        raise ArtifactError(f"expected .whl wheel: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) > MAX_ARCHIVE_MEMBERS:
                raise ArtifactError("wheel exceeds archive entry limit")
            if len(names) != len(set(names)):
                raise ArtifactError("wheel contains duplicate archive entries")
            unsafe = [n for n in names if not _valid_archive_path(n.rstrip("/"))]
            if unsafe:
                raise ArtifactError(f"wheel has unsafe entry path: {unsafe[0]!r}")
            meta = [n for n in names if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
            if len(meta) != 1:
                raise ArtifactError(f"wheel must contain exactly one .dist-info/METADATA (found {len(meta)})")
            base = meta[0].rsplit("/", 1)[0]
            # Wheel metadata is three required regular files, not merely
            # archive entries with the correct names. A directory or Unix
            # symlink at any of these paths must not satisfy the requirement.
            for required in ("METADATA", "WHEEL", "RECORD"):
                member_name = f"{base}/{required}"
                if member_name not in names:
                    raise ArtifactError(f"wheel missing {member_name}")
                member = archive.getinfo(member_name)
                mode = (member.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise ArtifactError(f"wheel: {required} must not be a symlink")
                if member.is_dir() or mode not in (0, 0o100000):
                    raise ArtifactError(f"wheel: {required} must be a regular file")
            info = archive.getinfo(meta[0])
            if info.file_size > MAX_METADATA_BYTES:
                raise ArtifactError("wheel: METADATA exceeds metadata size limit")
            # Bound decompression even if the ZIP header has misleading sizes.
            with archive.open(info) as stream:
                data = stream.read(MAX_METADATA_BYTES + 1)
            if len(data) > MAX_METADATA_BYTES:
                raise ArtifactError("wheel: METADATA exceeds metadata size limit")
            metadata = _decode_metadata(data, meta[0])
            expected = metadata["name"][0]
            wheel_parts = path.name[:-4].split("-")
            if len(wheel_parts) not in (5, 6) or not all(wheel_parts):
                raise ArtifactError("wheel filename: expected distribution-version[-build]-python-abi-platform.whl")
            # The optional wheel build tag is required to begin with a digit
            # by the wheel filename specification (PEP 427).
            if len(wheel_parts) == 6 and wheel_parts[2][0] not in "0123456789":
                raise ArtifactError("wheel filename: build tag must start with a digit")
            wheel_name, wheel_version = wheel_parts[:2]
            dist_info_name, dist_info_version = _identity_from_stem(
                base.removesuffix(".dist-info"), "wheel dist-info directory"
            )
            if not _name_matches_metadata(wheel_name, expected):
                raise ArtifactError("wheel filename distribution name differs from METADATA Name")
            if not _name_matches_metadata(dist_info_name, expected):
                raise ArtifactError("wheel dist-info directory distribution name differs from METADATA Name")
            version = metadata["version"][0]
            if _obvious_version_conflict(wheel_version, version):
                raise ArtifactError("wheel filename distribution version differs from METADATA Version")
            if _obvious_version_conflict(dist_info_version, version):
                raise ArtifactError("wheel dist-info directory distribution version differs from METADATA Version")
            return metadata
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise ArtifactError(f"could not read wheel {path}: {exc}") from exc


def _version_pair(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)", text.strip())
    if not match:
        raise ArtifactError(f"unrecognized Metadata-Version: {text!r}")
    # Trim leading zeros before int conversion and bound the remaining digits.
    # A malformed multi-thousand-digit Metadata-Version must yield ArtifactError,
    # rather than Python's integer-conversion ValueError escaping the CLI.
    major_text = match.group(1).lstrip("0") or "0"
    minor_text = match.group(2).lstrip("0") or "0"
    if len(major_text) > 6 or len(minor_text) > 6:
        raise ArtifactError("Metadata-Version numeric components exceed supported range")
    major, minor = int(major_text), int(minor_text)
    if major > SUPPORTED_METADATA_MAJOR:
        raise ArtifactError(
            f"unsupported Metadata-Version major {major} (supports {SUPPORTED_METADATA_MAJOR}.x): {text!r}"
        )
    return major, minor


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _dynamic_csv_items(field: str, values: list[str]) -> list:
    """Parse existing items for the PEP 808 append-only comparison.

    Keywords are comma-delimited terms. Address headers use RFC 822 syntax
    so quoted display names may themselves contain commas.
    """
    if not values:
        return []
    if field == "keywords":
        return [item.strip() for item in values[0].split(",")]
    return getaddresses(values)


def compare(sdist: Path, wheel: Path) -> Report:
    """Compare archives from the same build; no unpacking, imports or execution."""
    sm = _sdist_metadata(sdist)
    wm = _wheel_metadata(wheel)
    findings: list[Finding] = []

    def add(code: str, severity: str, message: str, field: str | None = None) -> None:
        findings.append(Finding(code, severity, message, field))

    project = sm["name"][0]
    version = sm["version"][0]
    if _normalize_name(project) != _normalize_name(wm["name"][0]):
        add("NAME_MISMATCH", "error", f"Name differs: {project!r} vs {wm['name'][0]!r}", "Name")
    if version != wm["version"][0]:
        add("VERSION_MISMATCH", "error", f"Version differs: {version!r} vs {wm['version'][0]!r}", "Version")

    s_version = _version_pair(sm["metadata-version"][0])
    w_version = _version_pair(wm["metadata-version"][0])
    for artifact, metadata_version in (("sdist", s_version), ("wheel", w_version)):
        if metadata_version[0] == SUPPORTED_METADATA_MAJOR and metadata_version[1] > MAX_SUPPORTED_METADATA_MINOR:
            add(
                "FUTURE_METADATA_VERSION", "warning",
                f"{artifact} uses Metadata-Version {metadata_version[0]}.{metadata_version[1]} above "
                f"the supported 2.{MAX_SUPPORTED_METADATA_MINOR}; performing best-effort checks"
            )
    if s_version < (2, 2):
        add("LEGACY_SDIST_METADATA", "warning", "sdist metadata predates 2.2; only Name/Version consistency is enforced")
        return Report(str(sdist), str(wheel), project, version, findings)

    dynamic = {v.strip().lower() for v in sm.get("dynamic", [])}
    for forbidden in ("name", "version", "metadata-version"):
        if forbidden in dynamic:
            add("INVALID_DYNAMIC_FIELD", "error", f"sdist must not mark {forbidden!r} as Dynamic", forbidden)
    # Metadata-Version and Dynamic are metadata control fields, not cross-artifact values.
    all_fields = (set(sm) | set(wm)) - EXCLUDED_METADATA_FIELDS - {"name", "version"}
    for field in sorted(all_fields):
        sv = sm.get(field, [])
        wv = wm.get(field, [])
        if field in dynamic:
            if s_version >= (2, 6) and sv:
                if field in MULTIPLE_USE_FIELDS:
                    original, built = sv, wv
                elif field in CSV_DYNAMIC_FIELDS:
                    original = _dynamic_csv_items(field, sv)
                    built = _dynamic_csv_items(field, wv)
                else:
                    # Ordinary single-use Dynamic fields remain free to change.
                    continue
                if built[:len(original)] != original:
                    add(
                        "DYNAMIC_BASELINE_CHANGED", "error",
                        f"Dynamic list field {field!r} must preserve source values in place, "
                        "with new entries appended", field
                    )
            continue
        if sv != wv:
            if field == "description":
                # Avoid dumping a potentially large/proprietary long description
                # into CI logs; report just presence, lengths and digests.
                def fingerprint(values: list[str]) -> str:
                    if not values:
                        return "missing"
                    value = values[0]
                    return f"length={len(value)} sha256={hashlib.sha256(value.encode('utf-8')).hexdigest()}"
                add("FIELD_MISMATCH", "error",
                    "Non-dynamic long-description text differs: "
                    f"sdist={fingerprint(sv)}; wheel={fingerprint(wv)}", field)
            else:
                add("FIELD_MISMATCH", "error",
                    f"Non-dynamic field {field!r} differs: sdist={sv!r}; wheel={wv!r}", field)
    if not findings:
        add("PARITY_OK", "info", "All checked metadata fields are consistent")
    return Report(str(sdist), str(wheel), project, version, findings)


def locate_distributions(dist_dir: Path) -> tuple[Path, Path]:
    if not dist_dir.is_dir():
        raise ArtifactError(f"distribution directory not found: {dist_dir}")
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(sdists) != 1 or len(wheels) != 1:
        raise ArtifactError(
            f"expected exactly one sdist and one wheel in {dist_dir} "
            f"(found {len(sdists)} sdists, {len(wheels)} wheels); provide explicit paths instead"
        )
    return sdists[0], wheels[0]
