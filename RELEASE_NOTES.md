## dist-parity 0.1.2

Maintenance release of the dependency-free Python 3.11+ sdist-to-wheel metadata checker and composite GitHub Action.

- Add optional paired `sdist` and `wheel` Action inputs for selecting a specific artifact pair in a multi-wheel build. Both inputs are required together; `dist-dir` continues to work.
- Reject provable numeric release-version conflicts between artifact filenames, archive metadata directories, and their declared versions; equivalent trailing-zero forms such as `1.0` and `1.0.0` remain accepted. Full PEP 440 normalization is intentionally out of scope.
- Run 43 maintainer-authored unit tests on Python 3.11, 3.12, and 3.13 and an integration workflow using real, publicly available package artifacts.

Install from the published GitHub release artifacts; PyPI and Marketplace publication are separate processes and are not implied by a GitHub release. Existing `v0.1.0` and `v0.1.1` tags/assets remain unchanged.

**Limitations:** Metadata consistency is not build provenance, a security audit, or proof of complete standards compliance. A mismatch can merit investigation without proving a backend bug. CI, self-authored tests, or publishing are **not evidence of independent users or downstream adoption**.
