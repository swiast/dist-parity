"""Read-only sdist/wheel metadata parity checks (PEP 643 / Core Metadata)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

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
            return _decode_metadata(stream.read(MAX_METADATA_BYTES + 1), meta_name)
    except (OSError, tarfile.TarError) as exc:
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
            info = archive.getinfo(meta[0])
            # Symlinks masquerading as METADATA should not be accepted as regular files.
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ArtifactError("wheel: METADATA must not be a symlink")
            for required in ("WHEEL", "RECORD"):
                if f"{base}/{required}" not in names:
                    raise ArtifactError(f"wheel missing {base}/{required}")
            if archive.getinfo(meta[0]).file_size > MAX_METADATA_BYTES:
                raise ArtifactError("wheel: METADATA exceeds metadata size limit")
            data = archive.read(meta[0])
            return _decode_metadata(data, meta[0])
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise ArtifactError(f"could not read wheel {path}: {exc}") from exc


def _version_pair(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)", text.strip())
    if not match:
        raise ArtifactError(f"unrecognized Metadata-Version: {text!r}")
    major, minor = int(match.group(1)), int(match.group(2))
    if major > SUPPORTED_METADATA_MAJOR:
        raise ArtifactError(
            f"unsupported Metadata-Version major {major} (supports {SUPPORTED_METADATA_MAJOR}.x): {text!r}"
        )
    return major, minor


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()



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
            if s_version >= (2, 6) and field in MULTIPLE_USE_FIELDS and sv and wv[:len(sv)] != sv:
                add("DYNAMIC_BASELINE_CHANGED", "error", f"Dynamic multivalued field {field!r} must preserve source values in place, with new entries appended", field)
            continue
        if sv != wv:
            add("FIELD_MISMATCH", "error", f"Non-dynamic field {field!r} differs: sdist={sv!r}; wheel={wv!r}", field)
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
