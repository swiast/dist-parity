# dist-parity

**Fail a release before inconsistent package metadata reaches Python users.**

`dist-parity` compares `PKG-INFO` in a Python source distribution (`sdist`) with `METADATA` inside its wheel, implementing the [Core Metadata](https://packaging.python.org/en/latest/specifications/core-metadata/) consistency relationship from [PEP 643](https://peps.python.org/pep-0643/). It is a dependency-free, read-only Python 3.11+ CLI and GitHub composite action.

## What it checks

- Sdist and wheel agree on distribution **Name** and **Version**.
- All non-`Dynamic` metadata fields match, for sdist metadata version 2.2+.
- `Dynamic` multivalued fields preserve their source values as an unchanged prefix (new values appended) when the source metadata version is 2.6+; earlier versions allow broader changes.
- Archives contain required metadata files; no suspicious traversal paths or duplicate wheel entries.
- Unknown future minor Core Metadata versions trigger warnings; unsupported future major versions fail closed.
- Machine-readable JSON is available for downstream CI tools.

**No network access, archive extraction or execution of the target package.**

## Install and run

From a clone of this repository:

```bash
python -m pip install .
python -m build  # run in your target Python package, requires the separate 'build' package
python -m dist_parity --dist-dir dist
```

Without cloning the source, you can install the tagged GitHub release directly (requires Git):

```bash
python -m pip install "git+https://github.com/swiast/dist-parity.git@v0.1.0"
```

**Version note:** The `v0.1.0` release is immutable. The latest `main` branch contains additional input-handling hardening and tests, which have not yet been included in a tagged release. See [CHANGELOG.md](CHANGELOG.md).

**PyPI status:** a manual, trusted publishing workflow is prepared, but a PyPI release has **not been verified**. Maintainers can follow the [PyPI setup guide](docs/PYPI_PUBLISHING.md); do not assume `pip install dist-parity` is available until PyPI lists the project.

Or install the checker in one environment and run it against explicit artifacts:

```bash
dist-parity --sdist dist/example-1.0.tar.gz --wheel dist/example-1.0-py3-none-any.whl
dist-parity --dist-dir dist --json
```

`--dist-dir` accepts exactly one `.tar.gz` and one `.whl`. When you build multiple platform wheels, invoke once per wheel with `--sdist` and `--wheel`.

## 30-second synthetic demonstration

No package registry or private artifacts are required. After installing the project
from this repository, run:

```bash
python examples/quickstart.py
```

This creates temporary synthetic sdist and wheel files that disagree on a
non-`Dynamic` `Requires-Python` field. The example succeeds **only if**
`dist-parity` reports the intentionally introduced metadata mismatch.
The files are deleted automatically. See the
[example source](examples/quickstart.py).

This is a maintainer-authored demonstration, **not** third-party adoption.

## GitHub Actions

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
- run: python -m pip install build
- run: python -m build
- uses: swiast/dist-parity@v0.1.0
  with:
    dist-dir: dist
```

Use this snippet **inside a job** that builds a Python distribution from its own source. The `swiast/dist-parity@v0.1.0` tag is published in [GitHub Releases](https://github.com/swiast/dist-parity/releases/tag/v0.1.0). For local development, set `PYTHONPATH=src` and run `python -m dist_parity --dist-dir dist`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Checked fields agree (warnings may be present) |
| `1` | Metadata inconsistency found |
| `2` | Invalid or ambiguous input artifacts |

## Example mismatch

```text
example 1.2.0: FAIL
  [error] FIELD_MISMATCH: Non-dynamic field 'requires-python' differs: sdist=['>=3.11']; wheel=['>=3.12']
```

## Scope and limitations

- **Use artifacts built from the same source distribution**, not an unrelated/prebuilt wheel. The packaging standard's static metadata rule is about wheels built from a given sdist.
- Older sdist metadata (before version 2.2) gets Name/Version comparison only, with a warning.
- Dynamic singleton fields may differ by design. For sdist metadata version 2.6+, dynamic multivalued fields keep their baseline values unchanged at the beginning, with only appended new entries; older metadata versions use the earlier rule.
- Checks email-style metadata **headers**, not long-description body semantics, dependency resolution, archive signatures, SBOM provenance, package reproducibility, or wheel RECORD cryptographic integrity.
- This is **not** a vulnerability scanner, proof of package integrity, installer, or replacement for `twine check`, `check-wheel-contents`, build/test workflows, and publisher attestations.
- Initial MVP supports one wheel at a time and does not infer whether two supplied artifacts actually originated from the same build.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m dist_parity --dist-dir dist
```

Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md). License: [MIT](LICENSE).

## Evidence, limitations, and review

- [Reproducible maintainer validation, limitations, and complementary tools](docs/VALIDATION.md)
- [Request for independent review and reproducible bug reports](docs/REVIEW_REQUEST.md)
- [Open investigation of packaging 25.0 metadata mismatch](https://github.com/swiast/dist-parity/issues/1)

Self-authored tests, issues and build logs are not evidence of third-party adoption. Independent use has not yet been established.

## Why this exists

Python releases often produce both a wheel and a source archive. Maintainers need a narrow, automatable signal that the two artifacts do not disagree about static metadata. `dist-parity` makes the PEP 643-specific comparison explicit and easy to embed in CI.

This project is independently created. It is not affiliated with OpenAI or the Python Packaging Authority.
