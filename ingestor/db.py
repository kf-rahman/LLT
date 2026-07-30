"""DocumentStore — Layer 1 persistence (the identity table).

One row per item, keyed by path. This is the record that makes ingestion
idempotent: it remembers each item's content hash, the recipe that processed it,
its trace id, and its status. `acl` is reserved for future permissions.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Document, Status

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    path         TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    class_key    TEXT,
    recipe_id    TEXT,
    trace_id     TEXT,
    status       TEXT NOT NULL,
    acl          TEXT,
    meta         TEXT,
    updated_at   TEXT NOT NULL
);
"""


class DocumentStore:
    def __init__(self, db_path: Path | str):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after a DB was first created (SQLite has no
        ADD COLUMN IF NOT EXISTS). Keeps existing state dirs working."""
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(documents)")}
        if "meta" not in cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN meta TEXT")

    def get(self, path: str) -> Document | None:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE path = ?", (path,)
        ).fetchone()
        return _row_to_doc(row) if row else None

    def upsert(self, doc: Document) -> None:
        self._conn.execute(
            """
            INSERT INTO documents
                (path, content_hash, class_key, recipe_id, trace_id, status, acl, meta, updated_at)
            VALUES (:path, :content_hash, :class_key, :recipe_id, :trace_id, :status, :acl, :meta, :updated_at)
            ON CONFLICT(path) DO UPDATE SET
                content_hash = excluded.content_hash,
                class_key    = excluded.class_key,
                recipe_id    = excluded.recipe_id,
                trace_id     = excluded.trace_id,
                status       = excluded.status,
                acl          = excluded.acl,
                meta         = excluded.meta,
                updated_at   = excluded.updated_at
            """,
            {
                "path": doc.path,
                "content_hash": doc.content_hash,
                "class_key": doc.class_key,
                "recipe_id": doc.recipe_id,
                "trace_id": doc.trace_id,
                "status": doc.status.value,
                "acl": doc.acl,
                "meta": json.dumps(doc.meta) if doc.meta else None,
                "updated_at": doc.updated_at,
            },
        )
        self._conn.commit()

    def set_status(self, path: str, status: Status) -> None:
        self._conn.execute(
            "UPDATE documents SET status = ? WHERE path = ?", (status.value, path)
        )
        self._conn.commit()

    def delete(self, path: str) -> None:
        self._conn.execute("DELETE FROM documents WHERE path = ?", (path,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _row_to_doc(row: sqlite3.Row) -> Document:
    return Document(
        path=row["path"],
        content_hash=row["content_hash"],
        class_key=row["class_key"],
        recipe_id=row["recipe_id"],
        trace_id=row["trace_id"],
        status=Status(row["status"]),
        acl=row["acl"],
        meta=json.loads(row["meta"]) if row["meta"] else {},
        updated_at=row["updated_at"],
    )
