from __future__ import annotations

import argparse
import os
import sys

from .html import write_report
from .summary import compute_summary, BenchmarkFileError, load_records
from .table import print_summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sphinx-benchmark",
        description=(
            "Summarise the sphinx_benchmarks.json written by the "
            "sphinx-benchmark extension during a Sphinx build."
        ),
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser(
        "run",
        help="render the recorded benchmarks",
        description="Render the recorded benchmarks as terminal tables or an HTML report.",
    )
    run.add_argument(
        "format",
        choices=("table", "html"),
        help="'table' prints the two summary tables; 'html' writes a static report",
    )
    run.add_argument(
        "-i",
        "--input",
        default="sphinx_benchmarks.json",
        metavar="JSON",
        help="path to the benchmarks JSON (default: %(default)s)",
    )
    run.add_argument(
        "-o",
        "--output-dir",
        default="sphinx_benchmark_report",
        metavar="DIR",
        help="directory for the HTML report; only used with 'html' (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``sphinx-benchmark`` console script.
    Returns exit code 0 on success.
    """
    args = _build_parser().parse_args(argv)

    try:
        data = load_records(args.input)
    except BenchmarkFileError as e:
        sys.exit(str(e))

    summary = compute_summary(data)

    if args.format == "table":
        print_summary(summary)
    else:
        out_dir = write_report(summary, args.output_dir)
        print(f"Report written: open {os.path.join(out_dir, 'index.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
