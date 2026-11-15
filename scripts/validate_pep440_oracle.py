"""Optional reference check of the stdlib-only PEP 440 identity heuristic.

Python Packaging is an independent *CI-only* oracle for valid PEP 440 version
spellings. The production checker must NEVER reject two versions that the
reference considers equal; it may conservatively defer some true differences.
No generated distributions, external user data or publication are involved.
"""
from __future__ import annotations

from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from packaging.version import Version  # CI-only reference dependency
from dist_parity.core import _obvious_version_conflict


def version_spellings() -> list[str]:
    """Bounded deterministic set of canonical and normalized PEP 440 aliases."""
    bases = ("0.9", "1", "1.0", "1.0.0", "2", "2.0", "3.0.1")
    suffixes = (
        "", "a0", "a1", "b01", "rc1", "rc2", ".post0",
        ".post1", ".dev0", ".dev1", "rc1.post2", ".post1.dev2",
        "+local", "rc1+local",
    )
    aliases = (
        "v1.0", "0!1.0", "1.0A01", "1.0alpha1", "1.0.a1",
        "1.0beta1", "1.0RC01", "1.0pre1", "1.0c1", "1.0-rc1",
        "1.0.post01", "1.0post1", "1.0-1", "1.0.post0",
        "1.0dev1", "1.0.dev01", "1.0+LOCAL", "1.0+alpha.01",
        "1!1.0", "1!1.0rc1", "2!1.0", "2!1.0.dev1",
        "3.0.0", "3.0.0rc1", "1.0rc", "1.0b",
    )
    return sorted(set(base + suffix for base in bases for suffix in suffixes) | set(aliases))


def check() -> dict[str, int]:
    versions = version_spellings()
    reference = {text: Version(text) for text in versions}
    equivalent = 0
    rejected = 0
    deferred = 0
    for first, second in product(versions, repeat=2):
        observed = _obvious_version_conflict(first, second)
        opposite = _obvious_version_conflict(second, first)
        if observed != opposite:
            raise AssertionError(f"asymmetric identity check: {first!r} / {second!r}")
        same = reference[first] == reference[second]
        if same:
            equivalent += 1
            if observed:
                raise AssertionError(
                    f"false mismatch for equivalent PEP 440 spellings: "
                    f"{first!r} == {second!r} ({reference[first]!r})"
                )
        elif observed:
            rejected += 1
        else:
            deferred += 1

    # These are examples of explicit, bounded claims, not a promise that
    # every valid, unequal PEP 440 pair will be reported by this heuristic.
    required_conflicts = (
        ("1.0rc1", "2.0rc1"),
        ("1.0rc1", "1.0rc2"),
        ("1.0a1", "1.0b1"),
        ("1.0.post0", "1.0.post1"),
        ("1.0.dev0", "1.0.dev1"),
        ("1!1.0", "2!1.0"),
    )
    for first, second in required_conflicts:
        if Version(first) == Version(second):
            raise AssertionError("invalid conflicting control")
        if not _obvious_version_conflict(first, second):
            raise AssertionError(f"known conflict was deferred: {first!r}, {second!r}")

    if equivalent < 150 or rejected < 1000 or deferred < 10:
        raise AssertionError(
            f"insufficient corpus discrimination: equivalent={equivalent} "
            f"rejected={rejected} deferred={deferred}"
        )

    return {
        "unique_valid_spellings": len(versions),
        "ordered_pairs": len(versions) ** 2,
        "reference_equivalent_pairs_not_rejected": equivalent,
        "proven_conflicts": rejected,
        "intentionally_deferred_conflicts": deferred,
        "false_positives": 0,
    }


if __name__ == "__main__":
    print("PASS: Python Packaging PEP 440 oracle (CI-only):", check())
