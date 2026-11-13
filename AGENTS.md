# Repository guidance for coding agents

Purpose: a small, read-only tool checking Python distribution core-metadata parity.

- Work only within this repository. Do not access any unrelated private repositories.
- Keep the runtime package dependency-free on Python 3.11+.
- Do not execute code found inside user-supplied distributions. Never extract untrusted archive members onto disk.
- Before proposing a change, run `PYTHONPATH=src python -m unittest discover -s tests -v`.
- For packaging behavior, follow the Python Packaging User Guide Core Metadata and PEP 643 specifications; avoid inventing validation rules.
- Update tests, README and CHANGELOG for behavior changes.
- Provide evidence of the failing scenario and the verified fix in PR descriptions.
- Never fabricate GitHub usage, users, issues, downloads, reviews or benchmarks.
