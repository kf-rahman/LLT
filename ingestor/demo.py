"""A small Claude-Code-style terminal UI for demoing the ingestion engine.

    python -m ingestor.demo

Pick a source, watch high-level one-line steps as it ingests, then ask questions
against the resulting corpus (retrieval with source citations).
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from .config import load_dotenv
from .connector import LocalFSConnector
from .orchestrator import Deps, ingest_event
from .query import search

_TTY = sys.stdout.isatty()
def _c(code: str) -> str:
    return code if _TTY else ""
DIM, BOLD, RESET = _c("\033[2m"), _c("\033[1m"), _c("\033[0m")
GREEN, CYAN, YELLOW = _c("\033[32m"), _c("\033[36m"), _c("\033[33m")


def _w(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()


class step:
    """Context manager rendering a one-line step: '▸ doing…' -> '✓ done'."""

    def __init__(self, msg: str):
        self.msg = msg
        self.final = msg

    def __enter__(self) -> "step":
        _w(f"  {DIM}▸ {self.msg}…{RESET}")
        self._t = time.time()
        return self

    def done(self, text: str) -> None:
        self.final = text

    def __exit__(self, *exc) -> None:
        _w(f"\r  {GREEN}✓{RESET} {self.final}{' ' * 20}\n")


def _header() -> None:
    print()
    print(f"  {BOLD}Ingestor{RESET} {DIM}— agentic ingestion demo{RESET}")
    print(f"  {DIM}point at a source · it ingests · then ask questions{RESET}")
    print()


def _choose_source():
    print("  Choose a data source:")
    print(f"    {BOLD}1{RESET}) Readwise Reader {DIM}(your saved articles & PDFs){RESET}")
    print(f"    {BOLD}2{RESET}) Local folder")
    choice = input(f"  {CYAN}>{RESET} ").strip()
    if choice == "2":
        path = input(f"  {DIM}folder path:{RESET} ").strip()
        return LocalFSConnector(path, source="local"), "local folder"
    from .readwise import ReadwiseConnector
    return ReadwiseConnector(), "Readwise Reader"


def _ingest(deps: Deps, connector) -> tuple[int, int]:
    with step("Connecting to source") as s:
        events = list(connector.list_events())
        s.done(f"Connected — {len(events)} document(s) found")
    if not events:
        return 0, 0

    before = {r.class_key for r in deps.recipes.all()}
    outcomes = []
    with step("Inspecting first document & choosing how to process it") as s:
        outcomes.append(ingest_event(events[0], deps))
        after = {r.class_key for r in deps.recipes.all()}
        cls = outcomes[0].class_key
        if after - before:
            s.done(f"New data type {YELLOW}{cls}{RESET} — agent authored a recipe "
                   f"{DIM}(extract → chunk → embed → store){RESET}")
        else:
            s.done(f"Recognized {YELLOW}{cls}{RESET} — reusing a known recipe {DIM}(no re-thinking){RESET}")

    if len(events) > 1:
        with step(f"Applying the recipe to {len(events) - 1} more document(s)") as s:
            for e in events[1:]:
                outcomes.append(ingest_event(e, deps))
            s.done(f"Processed {len(outcomes)} documents {DIM}(recipe reused — deterministic){RESET}")

    committed = sum(o.committed for o in outcomes)
    skipped = sum(1 for o in outcomes if not o.committed and o.change.value == "unchanged")
    with step("Extracting, chunking & embedding") as s:
        note = f"{skipped} unchanged (skipped)" if skipped else "all new"
        s.done(f"Corpus ready — {deps.corpus.count()} chunks from {committed} document(s) {DIM}[{note}]{RESET}")
    return committed, deps.corpus.count()


def _query_loop(deps: Deps) -> None:
    print(f"\n  {DIM}Ask a question about your data — or 'exit'.{RESET}\n")
    while True:
        try:
            q = input(f"  {CYAN}?{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "q"):
            break
        hits = search(deps, q, k=3)
        if not hits:
            print(f"    {DIM}(nothing relevant found){RESET}\n")
            continue
        top = hits[0]
        print(f"    {top.snippet[:220]}")
        print(f"    {DIM}↳ source: {BOLD}{top.title}{RESET}{DIM}  (relevance {top.score:.2f}){RESET}")
        if len(hits) > 1:
            others = ", ".join(h.title[:32] for h in hits[1:])
            print(f"    {DIM}related: {others}{RESET}")
        print()
    print(f"\n  {DIM}Done.{RESET}\n")


def run(fresh: bool = True) -> int:
    load_dotenv()
    _header()
    state = Path(".ingestor-demo")
    if fresh and state.exists():
        shutil.rmtree(state)
    try:
        connector, label = _choose_source()
    except RuntimeError as e:
        print(f"  {YELLOW}!{RESET} {e}")
        return 1

    print(f"\n  {DIM}source: {label}{RESET}\n")
    deps = Deps.build(root=state)
    committed, chunks = _ingest(deps, connector)
    if chunks == 0:
        print(f"\n  {YELLOW}!{RESET} No data ingested (empty source?).")
        return 1
    print(f"\n  {GREEN}{BOLD}✓ Data is ready for query.{RESET}")
    _query_loop(deps)
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
