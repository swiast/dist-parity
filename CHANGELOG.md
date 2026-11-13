# Changelog

## Unreleased (main)

- Handle truncated gzip sdists as structured input errors (CLI exit status 2), not uncaught EOF exceptions.
- Reject archive distribution-name identity conflicts between source filename/root/PKG-INFO and wheel filename/.dist-info/METADATA; preserve valid wheel build tags.
- Read wheel `METADATA` through a size-bounded stream, even if archive headers are misleading.
- Add regression coverage for truncated sdists, bounded wheel metadata reads and oversized metadata.
- These changes are on `main` only; the immutable `v0.1.0` tag and its existing release assets are unchanged.

## 0.1.0 — released 2026-11-13

- Initial MIT-licensed Python 3.11+ CLI for comparing sdist `PKG-INFO` and wheel `METADATA` under PEP 643.
- Human-readable and JSON output with stable exit statuses.
- GitHub composite action, test matrix, and `v0.1.0` wheel/sdist release assets.
- Support for Core Metadata 2.6 `Dynamic` multiuse append-only checks; warn for unknown future minor versions and fail on unsupported major versions.

Release: https://github.com/swiast/dist-parity/releases/tag/v0.1.0

**Distribution note:** A GitHub release is verified; PyPI publication has not been independently verified.
