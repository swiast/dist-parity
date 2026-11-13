# Validation and ecosystem fit

This note records **maintainer-performed checks**, not independent adoption or an endorsement by the Python Packaging Authority.

## What has been verified

- The `v0.1.0` release publishes a source archive and wheel: https://github.com/swiast/dist-parity/releases/tag/v0.1.0
- CI exercises the CLI and regression tests on Python 3.11–3.13: https://github.com/swiast/dist-parity/actions
- A composite-action run validates a newly built set of the project's own distributions. The same workflow obtains the unrelated `packaging==25.0` sdist, builds a wheel from **that sdist**, and prints a parity diagnostic: https://github.com/swiast/dist-parity/actions/runs/43431651062
- The `packaging==25.0` test reports a **mismatch**, not a successful parity check: the rebuilt wheel contains `Import-Name: packaging`, while the sdist omits it. The CI log records source Metadata-Version 2.4, wheel Metadata-Version 2.5, and no Dynamic field in either. [Issue #1](https://github.com/swiast/dist-parity/issues/1) tracks the remaining cross-version interpretation question; pinned backend provenance is now recorded. **Do not describe this as an upstream packaging defect**.

## Pinned build-backend comparison (reproducible)

The same published `packaging==25.0` source distribution yields different metadata when built with different supported versions of its declared Flit backend (`flit_core >=3.3`):

| Build artifact | Metadata version | `Import-Name` | Parity |
| --- | --- | --- | --- |
| sdist `PKG-INFO` | 2.4 | absent | — |
| wheel rebuilt using `flit_core==3.12.0` | 2.4 | absent | PASS |
| wheel rebuilt using `flit_core==4.2.0` | 2.5 | `packaging` | MISMATCH |

[CI run with both pinned builds and full logs](https://github.com/swiast/dist-parity/actions/runs/43434676911). This demonstrates that metadata consistency diagnostics can change when a build backend is upgraded, without changing the source archive. It **does not** establish a bug in `packaging` or Flit. The open question is whether PEP 643's rule applies to fields introduced only after the sdist's metadata version; see [issue #1](https://github.com/swiast/dist-parity/issues/1).

**Upstream discussion status (2026-11-13):** [pypa/flit#845](https://github.com/pypa/flit/issues/845) was **closed**. A Flit maintainer explained that building a wheel from an sdist generates metadata anew rather than reading the sdist's `PKG-INFO`. That explains how a backend-version-dependent metadata difference can arise; it is **not** an endorsement, independent use, or a determination that this checker is compliant or that Flit is defective. The maintainer also identified the project's [no-LLM contribution policy](https://github.com/pypa/flit/blob/main/doc/development.rst). Our externally submitted text was AI-assisted and had not been screened against that policy. We will not submit further AI-generated issues, comments or PRs to Flit. The cross-version standards interpretation remains unresolved; the checker behavior is unchanged until supported by authoritative guidance.

## Scope: a narrow extra check

| Tool | Main check | What dist-parity adds |
| --- | --- | --- |
| [Twine check](https://twine.readthedocs.io/en/stable/) | Distribution long-description rendering | Comparison of static sdist metadata with a wheel built from it |
| [check-wheel-contents](https://github.com/jwodder/check-wheel-contents) | Structure and contents of wheels | Cross-artifact Core Metadata comparison |
| [pydistcheck](https://pydistcheck.readthedocs.io/en/latest/) | Distribution structure, portability and file hygiene | Focused PEP 643 `Dynamic` / static metadata consistency test |

These tools are complementary; this is not a claim of unique functionality or superiority.

## How to reproduce on your own project

1. Build an sdist with `python -m build --sdist`.
2. Build the wheel **from that exact sdist**, rather than comparing it with an independently downloaded wheel.
3. Run `dist-parity --sdist dist/your-project-1.0.tar.gz --wheel dist/your_project-1.0-*.whl --json`.
4. A `0` exit status means the fields checked by this version are consistent, not that the artifacts are secure or reproducible.

For an automated release job, use the [README GitHub Actions example](../README.md#github-actions).

## Known limits

- Single sdist / wheel pair at a time, no proof of build provenance, and no malicious-code detection.
- Does not validate every Core Metadata field's semantic syntax.
- Wheel `METADATA` from a separately obtained wheel may legitimately differ if the wheel has been repaired after its initial build; compare only a wheel built from the supplied sdist.
- Independent third-party adoption, production use, and upstream validation **have not been established**.

Sources: [Core Metadata](https://packaging.python.org/en/latest/specifications/core-metadata/), [PEP 643](https://peps.python.org/pep-0643/), [PEP 794](https://peps.python.org/pep-0794/).
