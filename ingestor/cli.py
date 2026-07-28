"""Command-line entry point.

    python -m ingestor.cli ingest <source_dir> [--source NAME] [--state DIR]

Points the local-FS connector at a directory and runs the ingestion loop,
printing a per-item summary. Re-running is idempotent (unchanged items skip).
"""

from __future__ import annotations

import argparse
from collections import Counter

from .connector import LocalFSConnector
from .orchestrator import Deps, ingest_source


def _cmd_ingest(args: argparse.Namespace) -> int:
    deps = Deps.build(root=args.state)
    connector = LocalFSConnector(args.source_dir, source=args.source)
    outcomes = ingest_source(connector, deps)

    for o in outcomes:
        flag = "✓" if o.committed else ("·" if o.change.value == "unchanged" else "✗")
        detail = o.class_key or ""
        if o.checks_failed:
            detail += f"  failed: {o.checks_failed}"
        if o.error:
            detail += f"  error: {o.error}"
        print(f"  {flag} {o.change.value:9} {o.path}  [{detail}]")

    counts = Counter(o.doc_status.value for o in outcomes)
    committed = sum(1 for o in outcomes if o.committed)
    print(f"\n{len(outcomes)} item(s): {committed} committed, "
          f"{dict(counts)} — state in {args.state}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingestor", description="Agentic ingestion engine")
    sub = parser.add_subparsers(dest="command", required=True)

    ing = sub.add_parser("ingest", help="ingest a local directory")
    ing.add_argument("source_dir", help="directory to ingest")
    ing.add_argument("--source", default="local", help="source name for identities")
    ing.add_argument("--state", default=".ingestor", help="state dir for the stores")
    ing.set_defaults(func=_cmd_ingest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
