# Released artifact installation and tagged Action smoke verification

These checks are maintainer-operated, **not** third-party adoption or production usage.

## v0.1.2 release inventory

- [GitHub release](https://github.com/swiast/dist-parity/releases/tag/v0.1.2), commit `74401c805508cfacab88e7c186c61ac5e6640001`.
- Wheel `dist_parity-0.1.2-py3-none-any.whl`: SHA-256 `f7404baf015ebea9a188764713839b5a0244d6237dfe46b12c5d2ff576f75aa1`.
- Sdist `dist_parity-0.1.2.tar.gz`: SHA-256 `40e61f0b8fdc9cb5a5e66fd3a561b7b314c744a9c431ecfc15cce89008d851da`.
- A public `release-sha256.txt` also records both digests.
- [Exact-head release CI 43525912471](https://github.com/swiast/dist-parity/actions/runs/43525912471) **SUCCESS**: tested Python 3.11–3.13, built the artifacts, published once, downloaded them, and compared their hashes.
- [Exact-head integration CI 43525912427](https://github.com/swiast/dist-parity/actions/runs/43525912427) **SUCCESS**.

GitHub returned `immutable: false` for this release. No existing release tags or assets were rewritten. Platform-level immutability is **not** claimed.

## Tagged release verification

The [release-smoke workflow](../.github/workflows/release-smoke.yml) is configured to:

1. Download and verify fixed v0.1.2 release hashes, install the **published wheel** on Python 3.11, 3.12 and 3.13, run console/module CLIs, check version 0.1.2 and exercise the synthetic negative control.
2. Run the **published** `swiast/dist-parity@v0.1.2` Action using default `dist-dir`, then with a specific `sdist`/`wheel` pair while a second wheel is present.
3. Assert that supplying only one of `sdist` or `wheel` fails.

A workflow definition is not itself evidence of a passing run; consult its public workflow results. No PyPI publication is triggered by this workflow.

## Historical v0.1.1 verification

[Smoke run 43484099851](https://github.com/swiast/dist-parity/actions/runs/43484099851) previously passed for the published v0.1.1 wheel across Python 3.11–3.13 and the tagged v0.1.1 Action. These historical bytes remain untouched.

## Evidence boundaries

Passing owner CI is evidence of release-installability and the exact tested Action behavior, not independent usage, downloads, downstream adoption, PyPI publication, Marketplace listing, artifact signatures or full packaging standards compliance.
