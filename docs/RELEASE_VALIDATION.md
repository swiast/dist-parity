# Released artifact installation and action smoke verification

This page describes **maintainer-operated release verification**, not external package
adoption or production use.

## What is tested

The [GitHub Action workflow](../.github/workflows/release-smoke.yml) performs two
independent release checks:

1. On Python 3.11, 3.12, and 3.13, it downloads the **existing GitHub release**
   `v0.1.1` wheel and source distribution. Before installing anything, it verifies
   both files against the SHA-256 digests below, then installs the **released wheel**
   (not a checkout or a locally rebuilt wheel), runs both CLI entry points,
   checks package version 0.1.1, and executes the synthetic negative-control demo.
2. In a separate job, it builds this repository's own distribution pair and uses
   the **tagged** composite action `swiast/dist-parity@v0.1.1`, not the local
   `uses: ./` development action.

## Immutable release inventory

- [GitHub release v0.1.1](https://github.com/swiast/dist-parity/releases/tag/v0.1.1)
- Wheel: `dist_parity-0.1.1-py3-none-any.whl`
  SHA-256 `2d9664238562ea969d93713cc8f68a6f00943155b24f82813f54a6908cfd7488`.
- Sdist: `dist_parity-0.1.1.tar.gz`
  SHA-256 `12ff6f78b27bbd0fc8ca72d4754f4b970125ad1fd5a1807b763f3ef57ce7a548`.

These digests come from the published GitHub release inventory. Workflow status
is not evidence of a successful test until an actual run completes successfully.

## Verified public CI evidence

The [main-branch release smoke run #43484099851](https://github.com/swiast/dist-parity/actions/runs/43484099851) completed **successfully** on 2026-11-13:
- Actual `v0.1.1` GitHub release wheel installed and its CLI/negative-control example passed on Python **3.11, 3.12 and 3.13**.
- Tagged `swiast/dist-parity@v0.1.1` composite action passed against a newly built local distribution pair.

The run and release asset SHA-256 digests are independently inspectable on public GitHub. All tests were initiated and maintained by this repository's owner; do not interpret these outcomes as third-party use.

## Scope and cautions

- The test establishes installability and basic CLI/action functionality of the
  **GitHub-released artifacts** under the specified environments.
- It does not establish PyPI availability, independent users or downstream
  integrations, artifact signatures, or full compliance with Python packaging
  standards. The negative control is synthetic and maintainer-authored.
- The workflow does not write to PyPI, upload packages, or modify external
  repositories; it uses only public release assets and temporary CI workers.
