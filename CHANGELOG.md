# Changelog

## Unreleased (main)

- Allow the composite Action to select a specific `sdist`/`wheel` artifact pair in multi-wheel builds; require both inputs and preserve the existing `dist-dir` default. These Action inputs are not present in the published `v0.1.1` tag.
- Reject unambiguous numeric distribution-version conflicts between artifact filenames, archive directories and their respective metadata; retain equivalent trailing-zero release forms.
- Keep the runtime dependency-free. Full PEP 440 version spelling normalization remains out of scope.

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
