"""CorpusStore — the searchable output (semantic memory).

Stores chunks keyed by owning document path, so a document's chunks can be
deleted as a unit when it is modified (delete-old-before-write). v1 is a simple
SQLite table behind this interface; a real vector DB slots in later. `acl` is
reserved for future permissions.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Chunk

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id  TEXT PRIMARY KEY,
    path      TEXT NOT NULL,
    region    TEXT NOT NULL,
    content   TEXT NOT NULL,
    embedding BLOB,
    acl       TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
"""


class CorpusStore:
    def __init__(self, db_path: Path | str):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def add_chunks(self, path: str, chunks: list[Chunk]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO chunks (chunk_id, path, region, content, embedding, acl)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(c.chunk_id, path, c.region, c.content, c.embedding, c.acl) for c in chunks],
        )
        self._conn.commit()

    def delete_by_path(self, path: str) -> int:
        cur = self._conn.execute("DELETE FROM chunks WHERE path = ?", (path,))
        self._conn.commit()
        return cur.rowcount

    def get_by_path(self, path: str) -> list[Chunk]:
        rows = self._conn.execute(
            "SELECT * FROM chunks WHERE path = ? ORDER BY chunk_id", (path,)
        ).fetchall()
        return [
            Chunk(
                chunk_id=r["chunk_id"],
                path=r["path"],
                region=r["region"],
                content=r["content"],
                embedding=r["embedding"],
                acl=r["acl"],
            )
            for r in rows
        ]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
