# Request for independent review

We are looking for feedback from Python package maintainers and release engineers on a small, read-only tool that compares static metadata in a source distribution and a wheel built from that source distribution.

Repository: https://github.com/swiast/dist-parity

## Fast review (no installation required)

Read [the scope and evidence](VALIDATION.md) and [the CLI implementation](../src/dist_parity/core.py). The main question is whether the tool catches a useful class of real release regressions **without flagging valid metadata changes**.

If you already build both wheel and sdist for your package, use the [release and action instructions](../README.md). No package secrets are needed. Please do not upload proprietary artifacts.

## Specific feedback that would help

- Are the `Dynamic` rules and 2.6 append-only behavior implemented correctly?
- Are there legitimate wheel-from-sdist builds that this checker falsely rejects?
- Is a GitHub Action step useful as part of a release pipeline?
- Does the `packaging==25.0` `Import-Name` observation reproduce, and what metadata versions or backend behavior explain it?

Please open a [GitHub issue](https://github.com/swiast/dist-parity/issues/new) with the checker version, relevant metadata headers, steps to reproduce and the expected vs actual result, or submit a small PR with a synthetic regression fixture.

Issue reports from people outside the maintainer's account will be treated as independent feedback. Self-tests, self-authored issues and CI logs will **not** be reported as third-party adoption.

This project is unaffiliated with PyPA and OpenAI.
