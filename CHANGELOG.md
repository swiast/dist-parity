# Changelog

## Unreleased (main)

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
