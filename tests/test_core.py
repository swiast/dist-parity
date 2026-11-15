"""Unit tests use synthetic distribution archives, never private project files."""
from __future__ import annotations

import io
import json
import os
import shutil
import struct
import subprocess
import textwrap
import tarfile
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from pathlib import Path

from dist_parity.cli import main
from dist_parity.core import ArtifactError, compare, locate_distributions, _obvious_version_conflict, _version_pair, _decode_metadata


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

    def test_nondynamic_description_body_change_is_detected_without_leaking_text(self):
        source = meta()
        changed = source.replace(b"Example description", b"Private altered text")
        sdist, wheel = make_pair(self.base, sdata=source, wdata=changed)
        report = compare(sdist, wheel)
        failures = [f for f in report.findings if f.field == "description"]
        self.assertEqual([f.code for f in failures], ["FIELD_MISMATCH"])
        self.assertIn("sha256=", failures[0].message)
        self.assertNotIn("Private altered text", failures[0].message)
        self.assertNotIn("Example description", failures[0].message)

    def test_nondynamic_description_body_removal_is_detected(self):
        source = meta()
        empty_body = source.split(b"\n\n", 1)[0] + b"\n\n"
        sdist, wheel = make_pair(self.base, sdata=source, wdata=empty_body)
        report = compare(sdist, wheel)
        self.assertFalse(report.ok)
        self.assertIn("description", [f.field for f in report.findings])
        self.assertIn("missing", next(f.message for f in report.findings if f.field == "description"))

    def test_header_and_body_description_with_same_content_match(self):
        header = b"Metadata-Version: 2.6\nName: sample-pkg\nVersion: 1.0\n"
        header_description = header + b"Description: first\n       |second\n\n"
        body_description = header + b"\nfirst\nsecond"
        sdist, wheel = make_pair(self.base, sdata=header_description, wdata=body_description)
        self.assertTrue(compare(sdist, wheel).ok)

    def test_dynamic_description_body_change_is_allowed(self):
        source = meta(Dynamic="Description")
        modified = meta().replace(b"Example description", b"Different body")
        sdist, wheel = make_pair(self.base, sdata=source, wdata=modified)
        self.assertTrue(compare(sdist, wheel).ok)

    def test_description_body_crlf_is_equivalent_to_lf(self):
        source = meta()
        sdist, wheel = make_pair(self.base, sdata=source, wdata=source.replace(b"\n", b"\r\n"))
        self.assertTrue(compare(sdist, wheel).ok)

    def test_non_utf8_description_body_is_an_input_error(self):
        invalid = meta().replace(b"Example description", b"\xff")
        sdist, wheel = make_pair(self.base, wdata=invalid)
        with self.assertRaisesRegex(ArtifactError, "core metadata must be UTF-8"):
            compare(sdist, wheel)

    def test_description_header_and_body_together_are_ambiguous(self):
        conflicting = meta(Description="Header text")
        sdist, wheel = make_pair(self.base, sdata=conflicting)
        with self.assertRaisesRegex(ArtifactError, "both header and body"):
            compare(sdist, wheel)

    def test_invalid_ascii_package_name_is_structured_input_error(self):
        for bad_name in ("-leading", "trailing_", "space name", "café", "slash/name"):
            with self.subTest(bad_name=bad_name):
                s, w = make_pair(self.base, sdict={"name": bad_name})
                with self.assertRaisesRegex(ArtifactError, "invalid Name field"):
                    compare(s, w)

    def test_wheel_invalid_name_is_rejected_before_comparison(self):
        s, w = make_pair(self.base, wdict={"name": "non ascii 名"})
        with self.assertRaisesRegex(ArtifactError, "invalid Name field"):
            compare(s, w)

    def test_valid_ascii_package_name_forms_remain_supported(self):
        for name in ("A", "a_b", "Two.Part", "ABC-xyz_123"):
            with self.subTest(name=name):
                content = meta(name=name)
                parsed = _decode_metadata(content, "synthetic")
                self.assertEqual(parsed["name"], [name])

    def test_non_ascii_metadata_version_numbers_are_rejected(self):
        for name in ("٢.6", "2.٦", "２.６"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ArtifactError, "unrecognized Metadata-Version"):
                    _version_pair(name)

    def test_metadata_version_major_zero_is_rejected(self):
        with self.assertRaisesRegex(ArtifactError, "invalid Metadata-Version major 0"):
            _version_pair("0.9")
        s, w = make_pair(self.base, sdict={"meta_version": "0.9"})
        with self.assertRaisesRegex(ArtifactError, "invalid Metadata-Version major 0"):
            compare(s, w)

    def test_bad_utf8_header_wheel_is_invalid_input_even_when_values_equal(self):
        corrupt = meta().replace(
            b"Version: 1.0", b"Version: 1.0\nSummary: malformed-\xff"
        )
        sdist, wheel = make_pair(self.base, sdata=corrupt, wdata=corrupt)
        with self.assertRaisesRegex(ArtifactError, "core metadata must be UTF-8"):
            compare(sdist, wheel)

    def test_bad_utf8_header_sdist_is_invalid_input(self):
        corrupt = meta().replace(
            b"Version: 1.0", b"Version: 1.0\nSummary: malformed-\xfe"
        )
        sdist, wheel = make_pair(self.base, sdata=corrupt)
        with self.assertRaisesRegex(ArtifactError, "core metadata must be UTF-8"):
            compare(sdist, wheel)

    def test_valid_utf8_nonascii_metadata_header_is_accepted(self):
        encoded = meta(Summary="Résumé – validation")
        sdist, wheel = make_pair(self.base, sdata=encoded, wdata=encoded)
        self.assertTrue(compare(sdist, wheel).ok)

    def test_bad_utf8_header_is_structured_cli_input_error(self):
        corrupt = meta().replace(
            b"Version: 1.0", b"Version: 1.0\nSummary: PRIVATE-\xff-BYTE"
        )
        sdist, wheel = make_pair(self.base, wdata=corrupt)
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = main(["--sdist", str(sdist), "--wheel", str(wheel), "--json"])
        self.assertEqual(status, 2)
        self.assertEqual(errors.getvalue(), "")
        response = json.loads(output.getvalue())
        self.assertFalse(response["ok"])
        self.assertEqual(response["findings"], [])
        self.assertIn("core metadata must be UTF-8", response["error"])
        self.assertNotIn("PRIVATE", response["error"])

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

    def test_sdist_filename_version_conflict(self):
        s, w = make_pair(self.base)
        s = s.rename(self.base / "sample_pkg-2.0.tar.gz")
        with self.assertRaisesRegex(ArtifactError, "sdist filename distribution version differs"):
            compare(s, w)

    def test_sdist_root_version_conflict(self):
        s, w = make_pair(self.base)
        with tarfile.open(s, "r:gz") as archive:
            members = [(m.name, archive.extractfile(m).read()) for m in archive.getmembers()]
        with tarfile.open(s, "w:gz") as archive:
            for name, data in members:
                info = tarfile.TarInfo(name.replace("sample_pkg-1.0/", "sample_pkg-2.0/"))
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        with self.assertRaisesRegex(ArtifactError, "sdist root directory distribution version differs"):
            compare(s, w)

    def test_wheel_filename_version_conflict(self):
        s, w = make_pair(self.base)
        w = w.rename(self.base / "sample_pkg-2.0-py3-none-any.whl")
        with self.assertRaisesRegex(ArtifactError, "wheel filename distribution version differs"):
            compare(s, w)

    def test_wheel_dist_info_version_conflict(self):
        s, w = make_pair(self.base)
        with zipfile.ZipFile(w, "w") as archive:
            archive.writestr("sample_pkg-2.0.dist-info/METADATA", meta())
            archive.writestr("sample_pkg-2.0.dist-info/WHEEL", "Wheel-Version: 1.0\\n")
            archive.writestr("sample_pkg-2.0.dist-info/RECORD", "")
        with self.assertRaisesRegex(ArtifactError, "wheel dist-info directory distribution version differs"):
            compare(s, w)

    def test_equivalent_numeric_release_versions_remain_valid(self):
        s, w = make_pair(self.base)
        s = s.rename(self.base / "sample_pkg-1.0.0.tar.gz")
        w = w.rename(self.base / "sample_pkg-1.0.0-py3-none-any.whl")
        self.assertTrue(compare(s, w).ok)

    def test_wheel_build_tag_accepted(self):
        s, w = make_pair(self.base)
        w = w.rename(self.base / "sample_pkg-1.0-1-py3-none-any.whl")
        self.assertTrue(compare(s, w).ok)

    def test_long_summary_mismatch_is_bounded_and_digested(self):
        source_secret = "PRIVATE_SOURCE_" + "s" * 500
        wheel_secret = "PRIVATE_WHEEL_" + "w" * 500
        s, w = make_pair(self.base,
            sdict={"Summary": source_secret},
            wdict={"Summary": wheel_secret})
        report = compare(s, w)
        findings = [f for f in report.findings if f.field == "summary"]
        self.assertEqual(len(findings), 1)
        message = findings[0].message
        self.assertIn("sha256=", message)
        self.assertIn("count=1", message)
        self.assertNotIn(source_secret, message)
        self.assertNotIn(wheel_secret, message)
        self.assertLess(len(message), 400)

    def test_many_repeated_values_are_digested_instead_of_logged(self):
        values = [f"private-value-{i}" for i in range(30)]
        s, w = make_pair(self.base,
            sdict={"Classifier": values},
            wdict={"Classifier": values[:-1]})
        report = compare(s, w)
        message = next(f.message for f in report.findings if f.field == "classifier")
        self.assertIn("count=30", message)
        self.assertIn("sha256=", message)
        self.assertNotIn("private-value-29", message)
        self.assertLess(len(message), 400)

    def test_short_field_differences_remain_readable(self):
        s, w = make_pair(self.base,
            sdict={"Summary": "short-source"},
            wdict={"Summary": "short-wheel"})
        report = compare(s, w)
        message = next(f.message for f in report.findings if f.field == "summary")
        self.assertIn("short-source", message)
        self.assertIn("short-wheel", message)
        self.assertNotIn("summarized", message)

    def test_long_field_redacted_in_cli_json_and_human_output(self):
        secret = "PRIVATE_SENTINEL_" + "x" * 500
        make_pair(self.base, wdict={"Summary": secret})
        for extra_args in (["--json"], []):
            with self.subTest(extra_args=extra_args):
                output = io.StringIO()
                with redirect_stdout(output):
                    status = main(["--dist-dir", str(self.base), *extra_args])
                self.assertEqual(status, 1)
                self.assertNotIn(secret, output.getvalue())
                self.assertIn("sha256=", output.getvalue())
                if extra_args:
                    self.assertEqual(json.loads(output.getvalue())["findings"][0]["field"], "summary")

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

    def test_dynamic_keywords_may_append_in_metadata_26(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Keywords", "Keywords": "dog,puppy"},
            wdict={"Keywords": "dog, puppy, voting"})
        self.assertTrue(compare(s, w).ok)

    def test_dynamic_keywords_cannot_remove_reorder_or_modify_baseline(self):
        for wheel_keywords in ("puppy", "puppy,dog", "dog,cat", "doG,puppy"):
            with self.subTest(wheel_keywords=wheel_keywords):
                s, w = make_pair(self.base,
                    sdict={"Dynamic": "Keywords", "Keywords": "dog,puppy"},
                    wdict={"Keywords": wheel_keywords})
                report = compare(s, w)
                self.assertFalse(report.ok)
                self.assertIn("DYNAMIC_BASELINE_CHANGED", [f.code for f in report.findings])

    def test_dynamic_author_email_appends_with_comma_in_display_name(self):
        initial = '"Doe, Jane" <jane@example.org>, Joe <joe@example.org>'
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Author-Email", "Author_Email": initial},
            wdict={"Author_Email": initial + ", New Person <new@example.org>"})
        self.assertTrue(compare(s, w).ok)

    def test_dynamic_author_email_cannot_modify_initial_identity(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Author-Email", "Author_Email": '"Doe, Jane" <jane@example.org>'},
            wdict={"Author_Email": '"Doe, Jane" <other@example.org>, Bob <bob@example.org>'})
        report = compare(s, w)
        self.assertFalse(report.ok)
        self.assertIn("DYNAMIC_BASELINE_CHANGED", [f.code for f in report.findings])

    def test_dynamic_maintainer_email_cannot_remove_or_reorder(self):
        baseline = "first@example.org, second@example.org"
        for wheel_value in ("first@example.org", "second@example.org, first@example.org"):
            with self.subTest(wheel_value=wheel_value):
                s, w = make_pair(self.base,
                    sdict={"Dynamic": "Maintainer-Email", "Maintainer_Email": baseline},
                    wdict={"Maintainer_Email": wheel_value})
                report = compare(s, w)
                self.assertFalse(report.ok)
                self.assertIn("DYNAMIC_BASELINE_CHANGED", [f.code for f in report.findings])

    def test_older_25_dynamic_keywords_remain_unrestricted(self):
        s, w = make_pair(self.base,
            sdict={"meta_version": "2.5", "Dynamic": "Keywords", "Keywords": "a,b"},
            wdict={"meta_version": "2.5", "Keywords": "different"})
        self.assertTrue(compare(s, w).ok)

    def test_dynamic_csv_absent_in_source_may_be_added(self):
        s, w = make_pair(self.base,
            sdict={"Dynamic": "Keywords"},
            wdict={"Keywords": "alpha,beta"})
        self.assertTrue(compare(s, w).ok)

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

    def _make_late_deflate_error_sdist(self):
        """Build a valid initial tar prefix followed by an invalid DEFLATE block.

        BytesParser/tarfile can read the first members before zlib raises;
        this specifically covers the exception outside tarfile.open().
        """
        sdist, wheel = make_pair(self.base)
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w:") as archive:
            for index in range(12):
                if index == 0:
                    name, content = "sample_pkg-1.0/PKG-INFO", meta()
                elif index == 1:
                    name, content = "sample_pkg-1.0/pyproject.toml", b"[project]\nname='sample-pkg'\n"
                else:
                    name, content = f"sample_pkg-1.0/payload-{index}.bin", b"A" * 4096
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        # A raw DEFLATE non-final stored block followed by the reserved
        # BTYPE=3 block (0x06). The 16-KiB prefix is valid and large enough
        # for tarfile to successfully read some members before reaching it.
        prefix = tar_stream.getvalue()[:16384]
        length = len(prefix)
        stored_block = b"\x00" + struct.pack("<HH", length, length ^ 0xFFFF) + prefix
        sdist.write_bytes(bytes.fromhex("1f8b0800000000000003")
                          + stored_block + b"\x06" + b"\x00" * 8)
        return sdist, wheel

    def test_corrupt_gzip_deflate_after_valid_members_is_input_error(self):
        sdist, wheel = self._make_late_deflate_error_sdist()
        with self.assertRaisesRegex(ArtifactError, "could not read sdist"):
            compare(sdist, wheel)

    def test_corrupt_gzip_deflate_has_structured_cli_json_exit_two(self):
        sdist, wheel = self._make_late_deflate_error_sdist()
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = main(["--sdist", str(sdist), "--wheel", str(wheel), "--json"])
        self.assertEqual(status, 2)
        self.assertEqual(errors.getvalue(), "")
        result = json.loads(output.getvalue())
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"], [])
        self.assertIn("could not read sdist", result["error"])

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

    def test_wheel_build_tag_must_begin_with_digit(self):
        for invalid_tag in ("alpha", "١vendor"):
            with self.subTest(invalid_tag=invalid_tag):
                sdist, wheel = make_pair(self.base)
                wheel = wheel.rename(self.base / f"sample_pkg-1.0-{invalid_tag}-py3-none-any.whl")
                with self.assertRaisesRegex(ArtifactError, "build tag must start with a digit"):
                    compare(sdist, wheel)

    def test_wheel_build_tag_with_numeric_prefix_accepted(self):
        sdist, wheel = make_pair(self.base)
        wheel = wheel.rename(self.base / "sample_pkg-1.0-2vendor-py3-none-any.whl")
        self.assertTrue(compare(sdist, wheel).ok)

    def test_wheel_required_entries_reject_symlinks(self):
        for bad_field in ("METADATA", "WHEEL", "RECORD"):
            with self.subTest(bad_field=bad_field):
                sdist, wheel = make_pair(self.base)
                with zipfile.ZipFile(wheel, "w") as archive:
                    for field, content in (
                        ("METADATA", meta()), ("WHEEL", b"Wheel-Version: 1.0\\n"),
                        ("RECORD", b""),
                    ):
                        name = f"sample_pkg-1.0.dist-info/{field}"
                        if field == bad_field:
                            info = zipfile.ZipInfo(name)
                            info.create_system = 3
                            info.external_attr = (0o120777 << 16)
                            archive.writestr(info, b"elsewhere")
                        else:
                            archive.writestr(name, content)
                with self.assertRaisesRegex(ArtifactError, f"{bad_field} must not be a symlink"):
                    compare(sdist, wheel)

    def test_wheel_required_entries_reject_directory_modes(self):
        for bad_field in ("METADATA", "WHEEL", "RECORD"):
            with self.subTest(bad_field=bad_field):
                sdist, wheel = make_pair(self.base)
                with zipfile.ZipFile(wheel, "w") as archive:
                    for field, content in (
                        ("METADATA", meta()), ("WHEEL", b"Wheel-Version: 1.0\\n"),
                        ("RECORD", b""),
                    ):
                        name = f"sample_pkg-1.0.dist-info/{field}"
                        if field == bad_field:
                            # No trailing slash: is_dir() alone would miss this.
                            info = zipfile.ZipInfo(name)
                            info.create_system = 3
                            info.external_attr = (0o040755 << 16)
                            archive.writestr(info, b"")
                        else:
                            archive.writestr(name, content)
                with self.assertRaisesRegex(ArtifactError, f"{bad_field} must be a regular file"):
                    compare(sdist, wheel)

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

    def _run_composite_action(self, *, dist_dir=None, sdist="", wheel="", output_format="json", json_file=""):
        if shutil.which("bash") is None:
            self.skipTest("composite action requires Bash")
        # Execute the literal action run script in a GitHub-like environment:
        # avoids external YAML dependencies and exercises quoting/exit codes.
        action = (Path(__file__).resolve().parents[1] / "action.yml").read_text()
        self.assertEqual(action.count("      run: |"), 1)
        script = textwrap.dedent(action.split("      run: |", 1)[1])
        env = os.environ.copy()
        env.update({
            "DIST_PARITY_ACTION_PATH": str(Path(__file__).resolve().parents[1]),
            "DIST_PARITY_DIST_DIR": str(dist_dir or self.base),
            "DIST_PARITY_SDIST": str(sdist),
            "DIST_PARITY_WHEEL": str(wheel),
            "DIST_PARITY_FORMAT": output_format,
            "DIST_PARITY_JSON_FILE": str(json_file),
        })
        return subprocess.run(
            ["bash", "-c", script], env=env, cwd=self.base,
            capture_output=True, text=True, check=False
        )

    def test_action_json_dist_directory(self):
        make_pair(self.base)
        result = self._run_composite_action(dist_dir=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["project"], "sample-pkg")

    def test_action_json_incomplete_pair(self):
        sdist, _ = make_pair(self.base)
        result = self._run_composite_action(sdist=sdist)
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("--sdist and --wheel", payload["error"])

    def test_action_json_explicit_paths_with_spaces(self):
        folder = self.base / "artifacts with spaces"
        folder.mkdir()
        sdist, wheel = make_pair(folder)
        result = self._run_composite_action(sdist=sdist, wheel=wheel)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_action_can_save_json_report_to_path_with_spaces(self):
        make_pair(self.base)
        report_path = self.base / "report with spaces.json"
        result = self._run_composite_action(json_file=report_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(report_path.read_text()))
        self.assertTrue(json.loads(report_path.read_text())["ok"])

    def test_action_saves_json_even_when_checker_exits_two(self):
        sdist, _ = make_pair(self.base)
        report_path = self.base / "invalid-input.json"
        result = self._run_composite_action(sdist=sdist, json_file=report_path)
        self.assertEqual(result.returncode, 2)
        payload = json.loads(report_path.read_text())
        self.assertEqual(payload, json.loads(result.stdout))
        self.assertFalse(payload["ok"])
        self.assertIn("--sdist and --wheel", payload["error"])

    def test_action_json_file_rejected_in_text_mode(self):
        make_pair(self.base)
        target = self.base / "must-not-exist.json"
        result = self._run_composite_action(output_format="text", json_file=target)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(target.exists())
        self.assertIn("json-file requires format: json", result.stderr)

    def test_action_invalid_format_is_input_error(self):
        make_pair(self.base)
        result = self._run_composite_action(output_format="xml")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("format must be text or json", result.stderr)

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


    def test_json_missing_paired_artifact_arguments(self):
        for argv in (
            ["--json", "--sdist", "source.tar.gz"],
            ["--wheel", "wheel.whl", "--json"],
            ["--sdist", "source.tar.gz", "--json"],
        ):
            with self.subTest(argv=argv):
                output, errors = io.StringIO(), io.StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    status = main(argv)
                self.assertEqual(status, 2)
                self.assertEqual(errors.getvalue(), "")
                payload = json.loads(output.getvalue())
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["findings"], [])
                self.assertIn("--sdist and --wheel", payload["error"])

    def test_json_invalid_argument_and_exclusive_options(self):
        for argv in (
            ["--json", "--unknown"],
            ["--json", "--dist-dir", "dist", "--sdist", "source.tar.gz", "--wheel", "wheel.whl"],
        ):
            with self.subTest(argv=argv):
                output, errors = io.StringIO(), io.StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    status = main(argv)
                self.assertEqual(status, 2)
                self.assertEqual(errors.getvalue(), "")
                payload = json.loads(output.getvalue())
                self.assertFalse(payload["ok"])
                self.assertTrue(payload["error"])

    def test_plain_invalid_arguments_preserve_argparse_exit(self):
        errors = io.StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as context:
            main(["--sdist", "source.tar.gz"])
        self.assertEqual(context.exception.code, 2)
        self.assertIn("usage:", errors.getvalue())

    def test_very_long_numeric_release_components_are_safe(self):
        giant = "9" * 5000
        self.assertFalse(_obvious_version_conflict(giant, giant))
        self.assertTrue(_obvious_version_conflict(giant, "8" * 5000))
        self.assertFalse(_obvious_version_conflict("0" * 5000 + "1.0", "1"))
        self.assertTrue(_obvious_version_conflict("0" * 5000 + "1.0", "2"))

    def test_oversized_core_metadata_version_is_a_structured_error(self):
        s, w = make_pair(self.base, sdict={"meta_version": "2." + "9" * 5000})
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = main(["--sdist", str(s), "--wheel", str(w), "--json"])
        self.assertEqual(status, 2)
        self.assertEqual(errors.getvalue(), "")
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("Metadata-Version numeric components", payload["error"])
        with self.assertRaisesRegex(ArtifactError, "numeric components"):
            _version_pair("2." + "9" * 5000)


if __name__ == "__main__":
    unittest.main()
