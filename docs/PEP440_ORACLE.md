# Optional PEP 440 reference-oracle check

The package keeps a **stdlib-only runtime** and a deliberately conservative
version-identity heuristic: it identifies *provable* filename/metadata version
conflicts but does not purport to implement the complete PEP 440 grammar.

As this heuristic becomes more capable, the central safety property is:

**It must never reject a pair of valid PEP 440 spellings which the Python
Packaging reference library treats as the same version.**

The read-only CI job
[`PEP 440 reference oracle`](../.github/workflows/version-oracle.yml) checks
the current source's `_obvious_version_conflict` against
`packaging.version.Version`, using **packaging==26.3** installed only in CI.
The optional local reproduction is:

```bash
python -m pip install 'packaging==26.3'
python scripts/validate_pep440_oracle.py
```

The deterministic corpus covers 123 version spellings (7 release baselines
with many canonical pre/post/dev/local suffixes and extra aliases), yielding
15,129 ordered comparisons. Each must be symmetric. Every pair considered
equivalent by the reference library must **not** be marked conflicting by our
heuristic; a small set of unmistakable conflicts must be detected.

The report separately counts proven conflicts and **deferred** unequal
versions. Deferred differences are expected, not a pass claim for all
unequal PEP 440 spellings. It is *not* a completeness test, a substitute for
actual wheel/sdist integration, or a proof that the entire PEP 440 standard is
implemented. The production package does not import or require `packaging`;
the reference only runs in optional CI or local developer checks.

The existing published `v0.1.2` wheel is not updated by these checks. The
report covers code at a fixed GitHub CI commit and does not establish
independent third-party use or any application-program eligibility.
