"""Tracer — the append-only provenance log (episodic memory).

Records what the system did to each item, keyed by trace_id. Two record types:
  - decision: a routing/authoring choice, with a `why`.
  - event:    a tool ran / an outcome, with `ok` and metrics.

Append-only: never edit or delete past lines. Designed so an OpenTelemetry /
Phoenix sink can replace the JSONL writer later without changing callers.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .models import utcnow_iso


class Tracer:
    def __init__(self, log_path: Path | str):
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def new_trace(self, path: str) -> str:
        return uuid.uuid4().hex[:12]

    def _write(self, record: dict[str, Any]) -> None:
        record["ts"] = utcnow_iso()
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def decision(self, trace_id: str, path: str, why: str, **fields: Any) -> None:
        self._write({"type": "decision", "trace_id": trace_id, "path": path, "why": why, **fields})

    def event(self, trace_id: str, path: str, ok: bool, **fields: Any) -> None:
        self._write({"type": "event", "trace_id": trace_id, "path": path, "ok": ok, **fields})

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return [json.loads(line) for line in self._path.read_text().splitlines() if line.strip()]
