"""CLI entry point for the synthetic data generator."""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from synthetic_data.pipeline import run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="synthetic-data",
        description="Generate synthetic test data for full path coverage of Java methods.",
    )
    parser.add_argument(
        "source",
        help="Path to a .java source file or directory of .java files",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: dataset.csv or dataset.json)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "-m", "--method",
        help="Only analyze this method name",
    )
    parser.add_argument(
        "--no-boundary",
        action="store_true",
        help="Skip boundary value generation",
    )
    parser.add_argument(
        "--no-edge-cases",
        action="store_true",
        help="Skip edge case generation",
    )
    parser.add_argument(
        "--call-chain",
        action="store_true",
        help="Enable inter-procedural call chain analysis (inline same-class callees)",
    )
    parser.add_argument(
        "--inline-depth",
        type=int,
        default=2,
        help="Maximum call inlining depth (default: 2)",
    )
    parser.add_argument(
        "--max-paths",
        type=int,
        default=256,
        help="Maximum paths before stopping inlining (default: 256)",
    )
    parser.add_argument(
        "--schema",
        help="Path to sample CSV directory for column ordering (T_*.csv files)",
    )
    parser.add_argument(
        "--entity-dir",
        help="Path to directory with entity Java files (@Column annotations)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for directory processing (default: 4)",
    )

    args = parser.parse_args(argv)
    source = Path(args.source)

    if not source.exists():
        print(f"Error: {source} does not exist", file=sys.stderr)
        sys.exit(1)

    # Collect .java files
    if source.is_dir():
        java_files = sorted(source.rglob("*.java"))
        if not java_files:
            print(f"Error: no .java files found in {source}", file=sys.stderr)
            sys.exit(1)
    else:
        if not source.suffix == ".java":
            print(f"Error: {source} is not a .java file", file=sys.stderr)
            sys.exit(1)
        java_files = [source]

    def _process_file(java_file: Path) -> None:
        output_path = args.output
        if output_path is None and len(java_files) > 1:
            output_path = str(java_file.with_suffix(f".{args.format}"))

        run(
            source_file=str(java_file),
            method_name=args.method,
            output_format=args.format,
            output_path=output_path,
            include_boundary=not args.no_boundary,
            include_edge_cases=not args.no_edge_cases,
            enable_call_chain=args.call_chain,
            inline_depth=args.inline_depth,
            max_paths=args.max_paths,
            entity_dir=args.entity_dir,
            schema_dir=args.schema,
        )

    for java_file in java_files:
        _process_file(java_file)


if __name__ == "__main__":
    main()
