"""Command line interface for dist-parity."""
import argparse
import json
import sys
from pathlib import Path
from .core import ArtifactError, compare, locate_distributions


class _JsonArgumentError(ValueError):
    """Argument error that can be rendered as JSON without exiting."""


class _JsonAwareArgumentParser(argparse.ArgumentParser):
    json_errors = False

    def error(self, message: str) -> None:
        if self.json_errors:
            raise _JsonArgumentError(message)
        super().error(message)


def main(argv: list[str] | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    parser = _JsonAwareArgumentParser(
        prog="dist-parity", description="Compare sdist PKG-INFO with wheel METADATA (PEP 643)."
    )
    # Invalid arguments must produce JSON even if --json appears after the error.
    parser.json_errors = "--json" in raw_argv
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dist-dir", type=Path, default=Path("dist"), help="directory with one .tar.gz and one .whl (default: dist)")
    group.add_argument("--sdist", type=Path, help="explicit sdist .tar.gz (requires --wheel)")
    parser.add_argument("--wheel", type=Path, help="explicit wheel .whl (requires --sdist)")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    try:
        args = parser.parse_args(raw_argv)
        if (args.sdist is None) != (args.wheel is None):
            parser.error("--sdist and --wheel must be provided together")
    except _JsonArgumentError as exc:
        print(json.dumps({"ok": False, "error": str(exc), "findings": []}, indent=2))
        return 2
    try:
        sdist, wheel = (args.sdist, args.wheel) if args.sdist else locate_distributions(args.dist_dir)
        report = compare(sdist, wheel)
    except ArtifactError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc), "findings": []}, indent=2))
        else:
            print(f"dist-parity: input error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"{report.project} {report.version}: {'PASS' if report.ok else 'FAIL'}")
        for item in report.findings:
            print(f"  [{item.severity}] {item.code}: {item.message}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
