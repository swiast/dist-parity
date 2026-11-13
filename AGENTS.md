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
- Before proposing a GitHub issue, comment or PR on any **third-party repository**, first read its current contribution guidelines and AI/LLM policy. Do not submit AI-assisted material where prohibited. Require a human to take ownership and review any allowed submission. Never treat a maintainer's response or a self-authored issue as accepted contribution or adoption.
