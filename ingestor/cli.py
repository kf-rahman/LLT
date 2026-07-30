"""Command-line entry point.

    python -m ingestor.cli ingest <source_dir> [--source NAME] [--state DIR]
    python -m ingestor.cli ingest-readwise [--updated-after ISO] [--state DIR]

Runs the ingestion loop over a source and prints a per-item summary. Re-running
is idempotent (unchanged items skip). A .env is auto-loaded for secrets like
READWISE_TOKEN.
"""

from __future__ import annotations

import argparse
from collections import Counter

from .config import load_dotenv
from .connector import LocalFSConnector
from .orchestrator import Deps, ingest_source


def _report(outcomes, state: str) -> int:
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
          f"{dict(counts)} — state in {state}")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    deps = Deps.build(root=args.state)
    connector = LocalFSConnector(args.source_dir, source=args.source)
    return _report(ingest_source(connector, deps), args.state)


def _cmd_ingest_readwise(args: argparse.Namespace) -> int:
    from .readwise import ReadwiseConnector

    deps = Deps.build(root=args.state)
    connector = ReadwiseConnector(updated_after=args.updated_after, location=args.location)
    return _report(ingest_source(connector, deps), args.state)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # pick up READWISE_TOKEN etc. from a gitignored .env

    parser = argparse.ArgumentParser(prog="ingestor", description="Agentic ingestion engine")
    sub = parser.add_subparsers(dest="command", required=True)

    ing = sub.add_parser("ingest", help="ingest a local directory")
    ing.add_argument("source_dir", help="directory to ingest")
    ing.add_argument("--source", default="local", help="source name for identities")
    ing.add_argument("--state", default=".ingestor", help="state dir for the stores")
    ing.set_defaults(func=_cmd_ingest)

    rw = sub.add_parser("ingest-readwise", help="ingest your Readwise Reader documents")
    rw.add_argument("--updated-after", default=None,
                    help="ISO-8601 datetime — only fetch docs changed since (incremental)")
    rw.add_argument("--location", default=None,
                    help="filter: new | later | shortlist | archive | feed")
    rw.add_argument("--state", default=".ingestor", help="state dir for the stores")
    rw.set_defaults(func=_cmd_ingest_readwise)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
