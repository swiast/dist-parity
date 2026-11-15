# Non-publishing release candidate preflight

This workflow is for **maintainer preparation only**. It does not create a tag,
GitHub Release, GitHub Marketplace listing, PyPI release, or OpenAI application.
A passing run does not establish independent adoption or prove all packaging
standards are satisfied.

## What it verifies

The [release-preflight workflow](../.github/workflows/release-preflight.yml):

1. Uses a public, read-only GitHub Actions job with `contents: read`.
2. Builds a source archive and a wheel **from that source archive** with
   `python -m build` on Python 3.13.
3. Compares that pair using the current source checkout of `dist-parity`.
4. Records an inspectable JSON receipt containing exact SHA-256 hashes and
   artifact byte counts; fails with exit 1 on a metadata inconsistency and
   exit 2 for invalid or ambiguous archives.
5. Installs the built wheel into a fresh virtual environment and runs its
   module CLI without importing the source checkout.
6. Displays the receipt's artifact digests in the workflow's job summary.

The normal source CI no longer contains a push-triggered GitHub release job
and never requests `contents: write`. This closes the previous conditional
auto-publication path for `v0.1.2`; the historical released tag and files
remain unchanged. The separate PyPI workflow is still manual-only with a
protected `pypi` environment. A new release needs a separately approved,
reviewed publication process.

It intentionally does **not** upload built wheels, sdists or receipts to
public release assets or an artifact store. The files remain inside the
ephemeral CI worker. A separate owner decision is required for publication.

## Local reproduction

From a clean clone of the public repository with Python 3.11+:

```bash
python -m pip install build
python -m build --outdir candidate-dist
PYTHONPATH=src python scripts/release_preflight.py \
  --dist-dir candidate-dist --output candidate-receipt.json
```

The tool only **reads** the two artifacts. It does not download dependencies
or build them itself. `python -m build` is a separate, potentially executable
build-backend step. Use trusted code and an isolated build environment.
Generate artifacts in an initially empty directory. The receipt is local;
do not upload it publicly if any metadata might be private.

The receipt has `schema_version: 1`, the checker version, status,
`provenance_verified: false`, exact per-file SHA-256/byte lengths and the
existing comparison report. Exit statuses match the CLI: `0` pass, `1`
mismatch, `2` invalid input. The comparison itself **cannot prove** that
user-supplied artifacts share provenance, which is why the workflow controls
how its pair is built. SHA-256 hashes identify bytes, not authenticity.

## Version and authorization boundary

As of the creation of this workflow, the official GitHub release remains
`v0.1.2`. The current `main` source contains newer unreleased changes while
`pyproject.toml` may still identify them as version `0.1.2`. Never claim
the resulting candidate wheel is the published release, overwrite historical
assets, or use its digests as an official release checksum.

Before any future release, the repository owner should separately approve a
new version number, review changelog and scope, verify a release-specific
candidate against a fixed commit, and decide whether to publish on GitHub,
PyPI or Marketplace. These gates are outside this preflight.
