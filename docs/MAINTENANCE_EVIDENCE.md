# Maintenance evidence and reviewer entry point

Evidence checkpoint: **2026-11-17**. This is a maintainer-authored index of public evidence, not an independent audit, adoption claim, or endorsement.

## What problem is being tested?

`dist-parity` is an MIT-licensed, dependency-free Python 3.11+ CLI and GitHub Action. It compares the static Core Metadata of an sdist and a wheel built from that sdist. The intended benefit is an extra release-pipeline check for metadata drift; it does not replace single-artifact validators, package tests, or publisher attestations. Its value to other maintainers still needs independent evaluation.

The [pinned public-package case](VALIDATION.md#pinned-build-backend-comparison-reproducible) demonstrates a backend-version-dependent `Import-Name` diagnostic. That is an observed checker result, not proof that Flit or packaging violates the standard. The cross-version interpretation remains [open](https://github.com/swiast/dist-parity/issues/1).

## Keep the release and source baselines separate

| Baseline | What the evidence supports | What it does not support |
| --- | --- | --- |
| Published [GitHub v0.1.2](https://github.com/swiast/dist-parity/releases/tag/v0.1.2) | An installable wheel, sdist and tagged Action; [release-path smoke checks](RELEASE_VALIDATION.md) | Newer main-only checks or Action JSON inputs |
| Source commit [`d7be9aec9a9001ba13d28357c8aae0e6aeb42b30`](https://github.com/swiast/dist-parity/commit/d7be9aec9a9001ba13d28357c8aae0e6aeb42b30) | 146 unit-test methods on Python 3.11-3.14 and the exact-commit workflows below | A new published version, complete standards compliance, or independent adoption |

At this checkpoint, the latest published release remains v0.1.2. New source behavior is unreleased even where source version strings still say 0.1.2. For source experiments, record the **Git commit**, not only `--version`. This page records a fixed validation baseline, not a promise that an arbitrary future main commit has passed.

## Exact-source validation receipts

Every run in this table targets the source commit above. The unit count is **146 distinct methods**, not 584 distinct tests; the four Python versions repeat those methods. Separate oracle comparisons are not included in that count.

| Workflow | Public receipt | Interpretation |
| --- | --- | --- |
| CI, Python 3.11-3.14 | [43758101898](https://github.com/swiast/dist-parity/actions/runs/43758101898) | Unit tests, demonstration, build and self-parity checks succeeded |
| Integration verification | [43758101842](https://github.com/swiast/dist-parity/actions/runs/43758101842) | Maintainer-operated real-public-package and Action checks succeeded |
| JSON report contract | [43758101850](https://github.com/swiast/dist-parity/actions/runs/43758101850) | Current-source JSON contract checks succeeded |
| PEP 440 reference oracle | [43758101922](https://github.com/swiast/dist-parity/actions/runs/43758101922) | The bounded version-heuristic oracle checks succeeded |
| Non-publishing release preflight | [43758101880](https://github.com/swiast/dist-parity/actions/runs/43758101880) | Candidate build, parity receipt and clean-environment installation succeeded; no release was published |

These are owner-operated checks. Passing CI does not establish that unrelated projects use the tool. Historical failures remain in workflow history; this table is not a claim that every past run passed.

## Two reproducible evaluation paths

**Published baseline:** follow [TRY_IT.md](TRY_IT.md). It installs the released wheel, then compares artifacts from a project you maintain. Its results apply to v0.1.2, not newer source-only behavior.

**Fixed source baseline:** inspect the public source, then run in a disposable development environment:

```bash
git clone https://github.com/swiast/dist-parity.git
cd dist-parity
git checkout --detach d7be9aec9a9001ba13d28357c8aae0e6aeb42b30
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
python examples/quickstart.py
```

Installing/building this trusted source is distinct from checking target archives. The checker itself does not execute or extract target package contents. Building someone else's package can execute its backend; use only authorized/trusted code in isolation. A metadata match is not a security clearance.

## Independent evidence: what is and is not established

At this checkpoint, independent users, substantive independent reviews and downstream integrations have **not been verified**. The review invitation [issue #7](https://github.com/swiast/dist-parity/issues/7) has no comments. Observed stars and release download counters are not verified unique users: ownership, CI traffic, repeated downloads and actual usage are not established.

A useful external report identifies the checker tag or SHA, the authorized project/build, reproduction steps, expected and actual results, and whether the author is affiliated with this project. A different GitHub username alone does not prove independence. Documentation-only review, negative feedback, a one-time trial and ongoing downstream integration must be recorded as different evidence categories. Do not request stars or manufactured testimonials.

## Boundaries and next useful work

The tool is not an installer, full wheel validator, RECORD-integrity verifier, provenance verifier, vulnerability scanner, or comprehensive decompression-bomb defense. See [scope and limitations](VALIDATION.md#known-limits).

Priority work is to evaluate usefulness and false positives on real authorized builds, resolve the cross-version metadata question when authoritative evidence is available, and deliberately prepare a new release if approved. Additional synthetic tests are valuable when they protect a real behavior, not as a substitute for user evidence. New tags, release assets, PyPI/Marketplace publication and external submissions require separate authorization. No grant application or private applicant data belongs in this public evidence index.
