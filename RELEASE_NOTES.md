## dist-parity 0.1.1

Maintenance release of a dependency-free, read-only Python metadata parity checker and GitHub Action.

- Reject distribution identity conflicts between sdist filename, sdist root directory and `PKG-INFO`, or wheel filename, `.dist-info` directory and `METADATA`.
- Handle truncated gzip archives as structured CLI input errors rather than unhandled exceptions.
- Read wheel metadata through a bounded stream to limit decompression memory consumption.
- Expand local regression coverage to 38 tests; validate on Python 3.11, 3.12 and 3.13.
- Keep stable human-readable/JSON results and exit status behavior.

**Important limits:** This checks selected metadata consistency between a wheel and its corresponding sdist, not provenance, security, vulnerability absence or complete standards compliance. Cross-metadata-version interpretation remains under investigation. No third-party adoption or PyPI publication is claimed.
