# Changelog

## 0.1.0 — initial proposed release

- Read-only PEP 643 metadata consistency checks for `.tar.gz` and `.whl` artifacts.
- Human-readable and JSON output with stable exit statuses.
- Composite GitHub Action and CI test matrix.

This is a prepared release; it has **not** been published to GitHub or PyPI.

- Pre-publication review: enforce Metadata 2.6 dynamic multiuse append-only behavior, including interleaving regression tests; bound archive entry counts.

- Final pre-publication audit: warn on metadata minor versions newer than 2.6, reject unsupported metadata majors, and prevent report version shadowing (28 local tests).
