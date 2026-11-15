# Changelog

## Unreleased (main)

- Validate the bounded UTF-8 `WHEEL` metadata file's mandatory single `Wheel-Version` header with ASCII major.minor syntax; fail closed on missing/duplicate/malformed or unsupported major versions, while retaining best-effort 1.x future minors. Seven synthetic regression methods, including CLI JSON exit 2. Still not a wheel installer or complete wheel validator.
- Require any top-level wheel `.data/` installation root to match the selected `.dist-info/` distribution/version stem, rejecting stray/multiple scheme roots while permitting legitimate nested directories and ordinary files. Five synthetic regression tests.
- Add an isolated Python Packaging 26.3 PEP 440 oracle CI check (Python 3.11/3.14) over 123 valid version spellings and 15,129 ordered pairs; verify no equivalent spelling is marked as an obvious conflict, test symmetry, and count deliberate deferrals. Runtime remains dependency-free; no release publication.
- Bound declared sdist TAR member sizes (2 GB each, 4 GB aggregate) during header enumeration to reject implausibly large headers before decompression/seek; three synthetic regressions including a header-only oversized member and exact boundary. This is not a comprehensive decompression-bomb defense.
- Reject provable canonical PEP 440 pre/post/dev stage-number conflicts (e.g. `1.0rc1` versus `1.0rc2`) in artifact identity, while preserving zero/case aliases and deliberately deferring noncanonical spellings or local-only differences. Five synthetic regression methods; runtime remains stdlib-only.
- Detect provable PEP 440 epoch/release-number mismatches in sdist/wheel identity when versions have recognized prerelease/post/dev/local suffixes, retaining conservative normalization for aliases, opaque versions and suffix-only differences. Six regression test methods; still stdlib-only.
- Reject wheels containing multiple top-level `.dist-info` metadata directories, including secondary directories without `METADATA`; four regressions cover ambiguity and allowed nested package/license/SBOM files.
- Catch unsupported ZIP compression methods while reading wheel METADATA and report a structured input error (CLI exit 2); add three synthetic regression tests for raw ZIP headers, JSON CLI and supported DEFLATE.
- Reject TAR/ZIP file or symlink entries used as parent directories by other archive members (e.g., `pkg/module.py` plus `pkg/module.py/child`), while retaining legitimate directory parents. Four synthetic regressions cover both formats and symlink cases.
- Reject ZIP file/directory path aliases and repeated trailing separators; reject colliding TAR names when they remain distinguishable after `tarfile` normalizes directory slashes. Four synthetic regressions cover archive ambiguity, existing TAR duplicate checks, and valid directory controls.
- Convert late gzip/DEFLATE `zlib.error` failures during sdist member iteration into structured `ArtifactError` input errors (exit 2), with two synthetic regression tests that reproduce corruption after valid tar members.
- Reject malformed UTF-8 bytes anywhere in Core Metadata before email-header parsing, preventing silent U+FFFD replacement from hiding corrupt metadata; four new regression tests and an updated invalid-body assertion.
- Remove legacy privileged, push-triggered v0.1.2 release job from normal CI; retain read-only verification and add four offline release-policy regression checks. Historical release assets remain unchanged and future publication requires separate owner approval.
- Publish a JSON Schema v1 for both completed comparison and input-error CLI responses, a consumer guide, and an isolated CI contract validator with real outputs and six negative controls (no new runtime dependency).
- Validate the mandatory Core Metadata `Name` header against ASCII distribution-name syntax and reject non-ASCII `Metadata-Version` digits or a major version of zero; five focused synthetic regression methods, without claiming full PEP 440 or metadata validation.
- Bound mismatch diagnostics for long or numerous metadata values using item counts, character lengths and stable SHA-256 fingerprints, retaining short inline values and existing finding codes; four synthetic regressions prevent large payloads appearing in text/JSON CI logs.
- Add an optional `json-file` Action input (requires `format: json`) so subsequent CI steps can consume the JSON report even when the checker fails; preserve 0/1/2 exit codes through Bash `pipefail`, add three unit tests and live Action integration assertions. Current source only, not published v0.1.2.
- Add a non-publishing release-candidate preflight: the current-source sdist/wheel parity receipt records SHA-256 digests, checks clean-venv wheel install in read-only CI, and never creates a tag/release or uploads candidate distributions; four synthetic tests.
- Compare static long-description content from the Core Metadata `Description` header or message body (2.1+ representation), while permitting declared Dynamic changes; normalize CRLF/folded header representation, reject ambiguous simultaneous forms, and redact description content in mismatch diagnostics (length + SHA-256). Seven synthetic tests.
- Expose optional `format: json` in the *unreleased* composite Action while preserving the default text output and valid JSON for incomplete explicit pairs; add four Bash-script regression tests plus GitHub integration coverage.
- Enforce the Core Metadata 2.6 / PEP 808 append-only baseline for comma-separated Dynamic `Keywords`, `Author-Email` and `Maintainer-Email` lists (using RFC 822-aware address parsing for quoted names), with seven synthetic tests; 2.2–2.5 behavior remains unchanged.
- Require the three mandatory wheel `.dist-info` metadata entries to be regular files rather than symlink or directory entries; reject malformed optional wheel build tags that do not start with a digit.
- Add four synthetic regressions for wheel metadata entry types and build-tag syntax. This is owner-directed validation, not independent adoption.
- Move checkout/setup-python workflow and example references to current v7 Actions; add Python 3.14 to source CI and tagged-release installation smoke coverage without changing published v0.1.2 assets.
- Make `--json` produce structured exit-2 errors for invalid command-line arguments, without changing human-readable argparse errors.
- Avoid Python integer-conversion crashes on untrusted, extremely long numeric version components and reject oversized Core Metadata version components cleanly.
- Add five maintainer-authored regression tests for CLI errors and oversized version handling; not evidence of external adoption.

- Add an opt-in public-package Flit comparison reproducer with fixed PyPI artifact SHA-256 pins and no-network synthetic self-tests. The optional `--execute` path intentionally runs third-party build backends in a temporary virtual environment; it is not part of the released v0.1.2 tag and is not evidence of independent adoption.

## 0.1.2 — release candidate

- Add optional paired `sdist`/`wheel` inputs to the composite Action for multi-wheel build outputs; retain the existing `dist-dir` default.
- Reject unambiguous numeric distribution-version conflicts between artifact filenames, archive directories and their respective metadata; retain equivalent trailing-zero release forms.
- Remain runtime dependency-free; full PEP 440 version spelling normalization stays out of scope.
- Expand maintainer regression coverage to 43 tests and validate on Python 3.11–3.13.

## 0.1.1 — maintenance release

- Reject conflicting package names across source archive filename/root metadata and wheel filename/.dist-info metadata; retain valid wheel build tags.
- Handle truncated gzip sdists as structured input errors (exit status 2).
- Read wheel metadata through a size-bounded stream, protecting against misleading ZIP headers.
- Add regression tests and verify metadata package version consistency in CI.
- The `v0.1.0` release tag and its assets remain unchanged.

## 0.1.0 — released 2026-11-13

- Initial MIT-licensed Python 3.11+ CLI for comparing sdist `PKG-INFO` and wheel `METADATA` under PEP 643.
- Human-readable and JSON output with stable exit statuses.
- GitHub composite action, test matrix, and `v0.1.0` wheel/sdist release assets.
- Support for Core Metadata 2.6 `Dynamic` multiuse append-only checks; warn for unknown future minor versions and fail on unsupported major versions.

Release: https://github.com/swiast/dist-parity/releases/tag/v0.1.0

**Distribution note:** GitHub releases are separate from PyPI; PyPI publication has not been independently verified.
