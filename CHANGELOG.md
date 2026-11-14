# Changelog

## Unreleased (main)

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
