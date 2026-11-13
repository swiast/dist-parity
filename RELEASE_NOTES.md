## dist-parity 0.1.0

Initial release of a read-only, dependency-free Python tool for comparing static metadata between a source distribution (`PKG-INFO`) and a wheel (`METADATA`), according to the Python Core Metadata specification.

- Python 3.11+ CLI with human-readable and JSON outputs
- GitHub composite action for package release workflows
- Metadata 2.2+ `Dynamic` handling, including Metadata 2.6 multiple-use retention
- Future Core Metadata minor versions warn; unsupported future major versions fail safely
- Archive validation and automated regression tests (28 passing in local Python 3.13)

**Scope:** validates metadata consistency for wheels built from the corresponding sdist. It does not scan vulnerabilities or prove archive integrity.
