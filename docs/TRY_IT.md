# Evaluate dist-parity on a Python package you maintain

We welcome independent **technical feedback**, including negative results and
documentation-only reviews. This is **not** an endorsement request or a request
for stars. If you have not run the tool, please say so.

## Quick first run (no PyPI registration required)

Requires Python 3.11+ and a Python project that builds sdist and wheel:

```bash
python -m pip install --no-deps "https://github.com/swiast/dist-parity/releases/download/v0.1.1/dist_parity-0.1.1-py3-none-any.whl"
python -m pip install build
python -m build --outdir .dist-parity-check
dist-parity --dist-dir .dist-parity-check --json
```

Run from your **project root** and start with an **empty**
`.dist-parity-check` output directory. The package is installed from the
immutable GitHub release asset, not from PyPI. The [public release-smoke CI]
(https://github.com/swiast/dist-parity/actions/runs/43484099851)
has already verified installability on Python 3.11, 3.12 and 3.13.

A checker exit code of `0` means all checked fields matched; `1`
identifies a metadata discrepancy that requires investigation; and `2`
means invalid or ambiguous artifacts. A mismatch by itself is **not**
proof of a backend bug or a packaging-standards violation. Comparing two
artifacts built independently, rather than a wheel built from the supplied
sdist, can produce misleading results.

If your build creates multiple wheels, pass explicit `--sdist` and
`--wheel` paths. Avoid sharing proprietary artifact files in public.

## Alternative: tagged GitHub Action

For a Python package's existing build job, the
[tagged Action example](../examples/workflow.yml) can be copied into
your workflow. Use a wheel built from the corresponding source distribution,
and ensure the distribution directory contains only one sdist/wheel pair.

## Please tell us what happened

Use the [structured feedback form]
(https://github.com/swiast/dist-parity/issues/new?template=feedback.yml)
to report whether you only read the docs, ran the tool locally, tried
the Action, or could not complete the test. Useful responses include:

- What sort of Python project/build setup you tested, if sharable
- Observed exit code and sanitized metadata findings
- Whether the tool found a meaningful problem or generated a false positive
- A link to **your own public** downstream integration, only if one exists

We count genuine outside evaluations separately from verified downstream CI
adoption. Reviews, installs, CI results and merged PRs by the repository
owner **never** count as independent adoption.

No privacy-sensitive information, proprietary distributions, or credentials
are needed. This project is not affiliated with PyPA or OpenAI.
