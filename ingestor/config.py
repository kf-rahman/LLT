"""Runtime paths for the ingestor's generated stores.

Everything the engine persists lives under a single, gitignored state dir so the
source tree stays clean and a fresh checkout starts empty. Callers may override
the root (tests use a temp dir) — nothing hard-codes an absolute path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_STATE_DIR = Path(".ingestor")


@dataclass(frozen=True)
class Paths:
    """Resolved locations of the four stores, rooted at a single state dir."""

    root: Path

    @classmethod
    def under(cls, root: Path | str = DEFAULT_STATE_DIR) -> "Paths":
        return cls(root=Path(root))

    @property
    def documents_db(self) -> Path:
        return self.root / "documents.db"

    @property
    def corpus_db(self) -> Path:
        return self.root / "corpus.db"

    @property
    def recipes_dir(self) -> Path:
        return self.root / "recipes"

    @property
    def trace_log(self) -> Path:
        return self.root / "traces.jsonl"

    def ensure(self) -> "Paths":
        """Create the state dir (and recipes subdir) if absent. Idempotent."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        return self
