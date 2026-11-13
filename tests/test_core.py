"""Unit tests use synthetic distribution archives, never private project files."""
from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

from dist_parity.cli import main
from dist_parity.core import ArtifactError, compare, locate_distributions


def meta(name="sample-pkg", version="1.0", meta_version="2.6", **fields):
    lines = [f"Metadata-Version: {meta_version}", f"Name: {name}", f"Version: {version}"]
    for key, values in fields.items():
        for value in values if isinstance(values, list) else [values]:
            lines.append(f"{key.replace('_','-')}: {value}")
    return ("\n".join(lines) + "\n\nExample description\n").encode()


def make_pair(base, sdata=None, wdata=None, sdict=None, wdict=None):
    base = Path(base)
    sdist = base / "sample_pkg-1.0.tar.gz"
    wheel = base / "sample_pkg-1.0-py3-none-any.whl"
    sdata = sdata or meta(**(sdict or {}))
    wdata = wdata or meta(**(wdict or {}))
    with tarfile.open(sdist, "w:gz") as out:
        for name, data in {
            "sample_pkg-1.0/PKG-INFO": sdata,
            "sample_pkg-1.0/pyproject.toml": b"[project]\nname='sample-pkg'\nversion='1.0'\n",
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            out.addfile(info, io.BytesIO(data))
    with zipfile.ZipFile(wheel, "w") as out:
        out.writestr("sample_pkg-1.0.dist-info/METADATA", wdata)
        out.writestr("sample_pkg-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
        out.writestr("sample_pkg-1.0.dist-info/RECORD", "")
    return sdist, wheel


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def test_matching_files(self):
        s, w = make_pair(self.base)
        result = compare(s, w)
        self.assertTrue(result.ok)
        self.assertEqual(result.findings[0].code, "PARITY_OK")
        self.assertEqual(result.project, "sample-pkg")
        self.assertEqual(result.version, "1.0")

    def test_normalized_name(self):
        s, w = make_pair(self.base, sdict={"name": "SAMPLE.PKG"}, wdict={"name": "sample-pkg"})
        self.assertTrue(compare(s, w).ok)

    def test_name_and_version_mismatch(self):
        s, w = make_pair(self.base, wdict={"name": "another", "version": "2.0"})
        with self.assertRaisesRegex(ArtifactError, "wheel filename distribution name differs"):
            compare(s, w)

    def test_distinct_valid_artifact_metadata_reports_name_and_version_mismatch(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "w") as out:
            out.writestr("another-2.0.dist-info/METADATA", meta(name="another", version="2.0"))
            out.writestr("another-2.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
            out.writestr("another-2.0.dist-info/RECORD", "")
        w = w.rename(self.base / "another-2.0-py3-none-any.whl")
        report = compare(s, w)
        self.assertFalse(report.ok)
        self.assertEqual({f.code for f in report.findings}, {"NAME_MISMATCH", "VERSION_MISMATCH"})

    def test_sdist_filename_identity_rejected(self):
        s, w = make_pair(self.base)
        s = s.rename(self.base / "unrelated-1.0.tar.gz")
        with self.assertRaisesRegex(ArtifactError, "sdist filename distribution name differs"):
            compare(s, w)

    def test_sdist_root_identity_rejected(self):
        s, w = make_pair(self.base)
        members = []
        with tarfile.open(s, "r:gz") as archive:
            for m in archive.getmembers():
                members.append((m.name, archive.extractfile(m).read()))
        with tarfile.open(s, "w:gz") as archive:
            for name, data in members:
                item = tarfile.TarInfo(name.replace("sample_pkg-1.0/", "different-1.0/"))
                item.size = len(data)
                archive.addfile(item, io.BytesIO(data))
        with self.assertRaisesRegex(ArtifactError, "sdist root directory distribution name differs"):
            compare(s, w)

    def test_wheel_filename_identity_rejected(self):
        s, w = make_pair(self.base)
        w = w.rename(self.base / "unrelated-1.0-py3-none-any.whl")
        with self.assertRaisesRegex(ArtifactError, "wheel filename distribution name differs"):
            compare(s, w)

    def test_wheel_dist_info_identity_rejected(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "w") as out:
            out.writestr("other_pkg-1.0.dist-info/METADATA", meta())
            out.writestr("other_pkg-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
            out.writestr("other_pkg-1.0.dist-info/RECORD", "")
        with self.assertRaisesRegex(ArtifactError, "wheel dist-info directory distribution name differs"):
            compare(s, w)

    def test_wheel_build_tag_accepted(self):
        s, w = make_pair(self.base)
        w = w.rename(self.base / "sample_pkg-1.0-1-py3-none-any.whl")
        self.assertTrue(compare(s, w).ok)

    def test_nondynamic_requires_python_mismatch(self):
        s, w = make_pair(self.base,
            sdict={"Requires_Python": ">=3.11"},
            wdict={"Requires_Python": ">=3.12"})
        result = compare(s, w)
        self.assertFalse(result.ok)
        self.assertIn("requires-python", [f.field for f in result.findings])

    def test_new_wheel_field_is_mismatch(self):
        s, w = make_pair(self.base, wdict={"Summary": "added"})
        self.assertFalse(compare(s, w).ok)

    def test_import_name_added_when_wheel_metadata_version_increases(self):
        # Regression: sdist metadata 2.4 omits Import-Name, rebuilt wheel 2.5 adds it.
        # Under Core Metadata / PEP 643, this is an observable static-field delta.
        s, w = make_pair(self.base,
            sdict={"meta_version": "2.4"},
            wdict={"meta_version": "2.5", "Import_Name": ["sample_pkg"]})
        report = compare(s, w)
        self.assertFalse(report.ok)
        self.assertIn("import-name", [finding.field for finding in report.findings])

    def test_dynamic_single_value_may_change(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Summary", "Summary": "old"},
            wdict={"Summary": "new"})
        self.assertTrue(compare(s, w).ok)

    def test_dynamic_multi_can_append(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Classifier", "Classifier": ["A", "B"]},
            wdict={"Classifier": ["A", "B", "C"]})
        self.assertTrue(compare(s, w).ok)

    def test_dynamic_multi_must_not_insert_between_baseline_values(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Classifier", "Classifier": ["A", "B"]},
            wdict={"Classifier": ["A", "C", "B"]})
        report = compare(s, w)
        self.assertFalse(report.ok)
        self.assertIn("DYNAMIC_BASELINE_CHANGED", [f.code for f in report.findings])

    def test_dynamic_multi_cannot_remove(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Classifier", "Classifier": ["A", "B"]},
            wdict={"Classifier": ["B", "C"]})
        self.assertFalse(compare(s, w).ok)
        self.assertEqual(compare(s, w).findings[0].code, "DYNAMIC_BASELINE_CHANGED")

    def test_dynamic_multi_cannot_reorder(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Requires-Dist", "Requires_Dist": ["a", "b"]},
            wdict={"Requires_Dist": ["b", "a"]})
        self.assertFalse(compare(s, w).ok)

    def test_older_dynamic_multi_may_change(self):
        # Metadata versions prior to 2.6 do not enforce retention of source values.
        s, w = make_pair(self.base,
            sdict={"meta_version": "2.4", "Dynamic": "Classifier", "Classifier": ["A", "B"]},
            wdict={"Classifier": ["C"]})
        self.assertTrue(compare(s, w).ok)

    def test_invalid_dynamic(self):
        s, w = make_pair(self.base, sdict={"Dynamic": "Name"})
        self.assertEqual(compare(s, w).findings[0].code, "INVALID_DYNAMIC_FIELD")

    def test_legacy_metadata_warnings_and_only_identity(self):
        s, w = make_pair(self.base,
            sdict={"meta_version": "2.1", "Summary": "old"},
            wdict={"Summary": "new"})
        report = compare(s, w)
        self.assertTrue(report.ok)
        self.assertEqual(report.findings[0].code, "LEGACY_SDIST_METADATA")

    def test_dynamic_multi_duplicate_baseline_is_preserved(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Classifier", "Classifier": ["A", "A"]},
            wdict={"Classifier": ["A", "B", "A"]})
        self.assertFalse(compare(s, w).ok)

    def test_future_minor_metadata_version_warns(self):
        s, w = make_pair(self.base, sdict={"meta_version": "2.7"}, wdict={"meta_version": "2.7"})
        report = compare(s, w)
        self.assertTrue(report.ok)
        self.assertEqual([f.code for f in report.findings], ["FUTURE_METADATA_VERSION", "FUTURE_METADATA_VERSION"])

    def test_unsupported_sdist_major_fails(self):
        s, w = make_pair(self.base, sdict={"meta_version": "3.0"})
        with self.assertRaisesRegex(ArtifactError, "unsupported Metadata-Version major"):
            compare(s, w)

    def test_unsupported_wheel_major_fails(self):
        s, w = make_pair(self.base, wdict={"meta_version": "3.0"})
        with self.assertRaisesRegex(ArtifactError, "unsupported Metadata-Version major"):
            compare(s, w)

    def test_truncated_gzip_returns_input_error(self):
        s, w = make_pair(self.base)
        s.write_bytes(s.read_bytes()[:-50])
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--sdist", str(s), "--wheel", str(w), "--json"])
        self.assertEqual(status, 2)
        self.assertIn("could not read sdist", json.loads(output.getvalue())["error"])

    def test_wheel_metadata_read_is_bounded_stream(self):
        s, w = make_pair(self.base)
        # Regressions to unbounded ZipFile.read should be rejected by this test.
        with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("unbounded ZIP read")):
            self.assertTrue(compare(s, w).ok)

    def test_wheel_metadata_size_limit(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "w", compression=zipfile.ZIP_DEFLATED) as out:
            out.writestr("sample_pkg-1.0.dist-info/METADATA", b"X" * 2_000_001)
            out.writestr("sample_pkg-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
            out.writestr("sample_pkg-1.0.dist-info/RECORD", "")
        with self.assertRaisesRegex(ArtifactError, "exceeds metadata size limit"):
            compare(s, w)

    def test_missing_archive(self):
        with self.assertRaises(ArtifactError):
            compare(self.base / "missing.tar.gz", self.base / "missing.whl")

    def test_missing_wheel_metadata(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "w") as out:
            out.writestr("nothing", "")
        with self.assertRaisesRegex(ArtifactError, "METADATA"):
            compare(s, w)

    def test_missing_sdist_pyproject(self):
        s, w = make_pair(self.base)
        with tarfile.open(s, "w:gz") as out:
            data = meta()
            info = tarfile.TarInfo("sample_pkg-1.0/PKG-INFO")
            info.size = len(data)
            out.addfile(info, io.BytesIO(data))
        with self.assertRaisesRegex(ArtifactError, "pyproject"):
            compare(s, w)

    def test_duplicate_sdist_archive_entries(self):
        s, w = make_pair(self.base)
        # A duplicate root metadata member creates ambiguous tarfile lookup behavior.
        with tarfile.open(s, "r:gz") as archive:
            members = [(m, archive.extractfile(m).read() if m.isfile() else None)
                       for m in archive.getmembers()]
        with tarfile.open(s, "w:gz") as out:
            for info, data in members:
                out.addfile(info, io.BytesIO(data) if data is not None else None)
            duplicate = tarfile.TarInfo("sample_pkg-1.0/PKG-INFO")
            data = meta()
            duplicate.size = len(data)
            out.addfile(duplicate, io.BytesIO(data))
        with self.assertRaisesRegex(ArtifactError, "duplicate"):
            compare(s, w)

    def test_wheel_metadata_symlink(self):
        s, w = make_pair(self.base)
        info = zipfile.ZipInfo("sample_pkg-1.0.dist-info/METADATA")
        info.create_system = 3
        info.external_attr = (0o120777 << 16)
        with zipfile.ZipFile(w, "w") as out:
            out.writestr(info, "elsewhere")
            out.writestr("sample_pkg-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
            out.writestr("sample_pkg-1.0.dist-info/RECORD", "")
        with self.assertRaisesRegex(ArtifactError, "symlink"):
            compare(s, w)

    def test_duplicate_wheel_archive_entries(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "a") as out:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out.writestr("sample_pkg-1.0.dist-info/RECORD", "")
        with self.assertRaisesRegex(ArtifactError, "duplicate"):
            compare(s, w)

    def test_path_traversal_wheel(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "a") as out:
            out.writestr("../readme", "abc")
        with self.assertRaisesRegex(ArtifactError, "unsafe"):
            compare(s, w)

    def test_paths_auto_detection(self):
        s, w = make_pair(self.base)
        self.assertEqual(locate_distributions(self.base), (s, w))
        (self.base / "extra.whl").write_bytes(b"")
        with self.assertRaisesRegex(ArtifactError, "exactly one"):
            locate_distributions(self.base)

    def test_cli_json_success(self):
        make_pair(self.base)
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--dist-dir", str(self.base), "--json"])
        self.assertEqual(status, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])

    def test_cli_json_failure(self):
        make_pair(self.base, wdict={"Summary": "extra"})
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--dist-dir", str(self.base), "--json"])
        self.assertEqual(status, 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_cli_missing_inputs(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--dist-dir", str(self.base), "--json"])
        self.assertEqual(status, 2)
        self.assertIn("expected exactly one", json.loads(output.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
