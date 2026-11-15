# dist-parity

**Fail a release before inconsistent package metadata reaches Python users.**

`dist-parity` compares `PKG-INFO` in a Python source distribution (`sdist`) with `METADATA` inside its wheel, implementing the [Core Metadata](https://packaging.python.org/en/latest/specifications/core-metadata/) consistency relationship from [PEP 643](https://peps.python.org/pep-0643/). It is a dependency-free, read-only Python 3.11+ CLI and GitHub composite action.

**Independent package-maintainer feedback wanted:** [review the tested v0.1.2 release or try it on your own sdist/wheel build](https://github.com/swiast/dist-parity/issues/7). Documentation-only and negative reviews are welcome; no stars, endorsements, or private artifacts requested. Owner-operated tests are not third-party use.

## Try it on your project (GitHub release; PyPI not required)

Install the **published v0.1.2 wheel** directly, without cloning or a PyPI account:

```bash
python -m pip install --no-deps "https://github.com/swiast/dist-parity/releases/download/v0.1.2/dist_parity-0.1.2-py3-none-any.whl"
python -m pip install build
python -m build --outdir .dist-parity-check
dist-parity --dist-dir .dist-parity-check --json
```

Run these commands in the **root of a Python project you maintain** with
a valid `pyproject.toml`. Use an **empty output directory** for each run.
`python -m build` normally builds the wheel from the just-built sdist.
Exit `0` means the fields checked by this tool matched, `1` means a
diagnostic mismatch worth investigating, and `2` means invalid/ambiguous
input. A mismatch is **not automatically a bug in your build backend**.

Prefer automation? See the [tagged GitHub Action example](examples/workflow.yml).
We would value [a brief public review, even from a first-time user](docs/REVIEW_REQUEST.md).
Please do not post proprietary archives, private names, tokens, or credentials.

## What it checks

- Sdist and wheel agree on distribution **Name** and **Version**; the required `Name` header must follow the ASCII package-name format, and `Metadata-Version` must use ASCII decimal components.
- All non-`Dynamic` metadata fields match, for sdist metadata version 2.2+, including long descriptions stored in the email body or the `Description` header.
- For source metadata 2.6+, `Dynamic` list fields retain their source entries as an unchanged prefix, allowing only appended entries. This includes repeated headers and the comma-separated `Keywords`, `Author-Email`, and `Maintainer-Email` lists (quoted email display names are parsed as addresses). Earlier metadata versions allow broader changes.
- Core Metadata headers and long descriptions must be valid UTF-8 byte streams; malformed encodings are rejected as input errors rather than silently replaced by the email parser.
- Corrupt gzip/DEFLATE input is reported as an invalid sdist (CLI exit 2), including corruption encountered after initially readable tar members; no unchecked traceback is exposed.
- Archives contain required metadata files; no suspicious traversal paths or duplicate wheel entries. ZIP entries with file/directory path aliases (`name` and `name/`) or repeated trailing separators are rejected; TAR entries are checked using the names exposed by Python's `tarfile` reader, which already normalizes some directory slashes. Ordinary directory entries remain accepted. Wheel `METADATA`, `WHEEL`, and `RECORD` must be regular ZIP file members, not symlinks or directories.
- Archive distribution-name identity matches across sdist filename/root/PKG-INFO and wheel filename/.dist-info/METADATA.
- Wheel filenames with an optional build tag require a leading digit, per the wheel format.
- Obviously conflicting numeric release versions in filenames/archive directories are rejected without treating equivalent forms such as `1.0` and `1.0.0` as different.
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
python -m pip install "git+https://github.com/swiast/dist-parity.git@v0.1.2"
```

**Version note:** `v0.1.2` adds explicit Action artifact inputs and numeric version checks. Older `v0.1.0` and `v0.1.1` tags and assets were not modified. GitHub currently reports `immutable: false` for `v0.1.2`; do not infer platform-enforced immutability. See [CHANGELOG.md](CHANGELOG.md).

**PyPI status:** a manual, trusted publishing workflow is prepared, but a PyPI release has **not been verified**. Maintainers can follow the [PyPI setup guide](docs/PYPI_PUBLISHING.md); do not assume `pip install dist-parity` is available until PyPI lists the project.

Or install the checker in one environment and run it against explicit artifacts:

```bash
dist-parity --sdist dist/example-1.0.tar.gz --wheel dist/example-1.0-py3-none-any.whl
dist-parity --dist-dir dist --json
```

`--dist-dir` accepts exactly one `.tar.gz` and one `.whl`. When you build multiple platform wheels, invoke once per wheel with `--sdist` and `--wheel`.

**Unreleased Action JSON mode (current `main`, not v0.1.2):** the composite Action
now accepts `format: json` (default: `text`). Optionally supply `json-file`
with a writable path in an existing directory to retain the JSON for subsequent
CI steps, including when the check exits with mismatch status 1 or input status
2. The Action preserves the original CLI exit code. Supplying `json-file` with
`format: text` is an invalid input (exit 2). JSON diagnostics use the CLI's
existing `--json` schema, including for incomplete explicit artifact pairs.
This feature is **not yet available** when using the published
`swiast/dist-parity@v0.1.2` tag; do not advertise it in tagged examples
until a new release is approved and verified. CI integrations requiring JSON
on v0.1.2 can invoke the installed CLI with `--json` directly.

**Action support for multi-wheel builds (`v0.1.2`):** the published composite Action accepts `sdist` and `wheel` inputs together, overriding `dist-dir`, so a build with multiple wheels can select each pair without moving files. Supplying just one input fails with exit 2. Invoke the Action once per intended wheel. The older `v0.1.1` tag supports `dist-dir` only.

## Release permission boundary

Normal `push` and `pull_request` CI has **read-only repository permissions**
and never creates a GitHub release, writes a tag or publishes to PyPI.
A former push-triggered GitHub `v0.1.2` release job has been removed to
avoid unintended publication if historical release state changes. The
existing `v0.1.2` tag and artifact digests are unchanged.

The [candidate preflight](docs/RELEASE_CANDIDATE.md) is deliberately
non-publishing. The separate [PyPI workflow](docs/PYPI_PUBLISHING.md)
remains manual-only and account/environment gated; running it requires
explicit owner approval. Any future new GitHub release must be separately
authorized and validated at its exact source commit.

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
- uses: actions/checkout@v7
- uses: actions/setup-python@v7
  with:
    python-version: '3.11'
- run: python -m pip install build
- run: python -m build
- uses: swiast/dist-parity@v0.1.2
  with:
    dist-dir: dist
```

Use this snippet **inside a job** that builds a Python distribution from its own source. The `swiast/dist-parity@v0.1.2` tag is published in [GitHub Releases](https://github.com/swiast/dist-parity/releases/tag/v0.1.2). For local development, set `PYTHONPATH=src` and run `python -m dist_parity --dist-dir dist`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Checked fields agree (warnings may be present) |
| `1` | Metadata inconsistency found |
| `2` | Invalid or ambiguous input artifacts |

### Machine-readable JSON and exit codes

A **versioned JSON Schema v1** and integration guidance are available in
[the JSON API contract](docs/JSON_API.md). The schema covers successful,
mismatching and invalid-input output shapes for the current source; it is
not a claim that unreleased Action options exist in the published v0.1.2.

Pass `--json` for a single JSON object on standard output, including
command-line argument failures (for example, `--sdist` without `--wheel`)
and malformed archives. Exit codes remain `0` for parity, `1` for a
metadata mismatch and `2` for invalid inputs.

Very long or numerous metadata values are summarized by item count, character
length and SHA-256 digest, rather than reproduced verbatim in log output. Short
values remain readable. This reduces log volume and incidental disclosure but
is **not** a confidentiality boundary: use private CI for sensitive projects.

On a completed comparison the object contains `sdist`, `wheel`,
`project`, `version`, `ok`, and `findings`. Each finding includes
`code`, `severity`, `message`, and `field`. Invalid arguments or
archives produce `{"ok": false, "error": "...", "findings": []}`;
`--help` intentionally retains normal human-readable argparse output.
Do not infer third-party usage from maintainer CI alone.

## Example mismatch

```text
example 1.2.0: FAIL
  [error] FIELD_MISMATCH: Non-dynamic field 'requires-python' differs: sdist=['>=3.11']; wheel=['>=3.12']
```

## Scope and limitations

- **Use artifacts built from the same source distribution**, not an unrelated/prebuilt wheel. The packaging standard's static metadata rule is about wheels built from a given sdist.
- Older sdist metadata (before version 2.2) gets Name/Version comparison only, with a warning.
- Dynamic singleton fields may differ by design. For sdist metadata version 2.6+, dynamic multivalued fields keep their baseline values unchanged at the beginning, with only appended new entries; older metadata versions use the earlier rule.
- Compares long-description text (including Core Metadata 2.1+ body form), normalizing CRLF/LF and standard folded header form. It does **not** check long-description markup rendering, dependency resolution, archive signatures, SBOM provenance, package reproducibility or wheel RECORD cryptographic integrity. Description mismatches are reported by length and SHA-256 rather than echoing their contents.
- This is **not** a vulnerability scanner, proof of package integrity, installer, or replacement for `twine check`, `check-wheel-contents`, build/test workflows, and publisher attestations.
- Initial MVP supports one wheel at a time and does not infer whether two supplied artifacts actually originated from the same build.

## Non-publishing release candidate check

Maintainers can run the [release candidate preflight](docs/RELEASE_CANDIDATE.md)
to build and inspect candidate wheel/sdist artifacts, record local SHA-256
evidence and smoke-install the wheel without creating a release. This workflow
uses the current source checkout (not the published `v0.1.2` wheel) and does
**not** constitute public publication or independent adoption.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m dist_parity --dist-dir dist
```

Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md). License: [MIT](LICENSE).

## Evidence, limitations, and review

- [Reproducible maintainer validation, limitations, and complementary tools](docs/VALIDATION.md)
- [Published v0.1.2 wheel installation and tagged Action smoke verification](docs/RELEASE_VALIDATION.md)
- [Request for independent review and reproducible bug reports](docs/REVIEW_REQUEST.md)
- [GitHub discovery, Marketplace publication readiness and adoption evidence levels](docs/DISCOVERABILITY.md)
- [Open investigation of packaging 25.0 metadata mismatch](https://github.com/swiast/dist-parity/issues/1)
- [Opt-in, hash-pinned reproducibility script for a real public-package case](examples/reproduce_flit_case.py) — safe `--dry-run` / `--self-test` by default; third-party code only with `--execute`

Self-authored tests, issues and build logs are not evidence of third-party adoption. Independent use has not yet been established.

## Why this exists

Python releases often produce both a wheel and a source archive. Maintainers need a narrow, automatable signal that the two artifacts do not disagree about static metadata. `dist-parity` makes the PEP 643-specific comparison explicit and easy to embed in CI.

This project is independently created. It is not affiliated with OpenAI or the Python Packaging Authority.
