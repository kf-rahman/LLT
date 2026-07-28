"""RecipeStore — Layer 2 persistence (procedural memory).

One JSON file per class, keyed by class_key. Small (one entry per class, not per
item), human-readable, and git-diffable. This is the "how to process X" memory
that a class HIT reuses with no LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Recipe


def _safe_name(class_key: str) -> str:
    # class keys may contain "+" and "::"; make a filesystem-safe basename.
    return class_key.replace("::", "__").replace("/", "_") + ".json"


class RecipeStore:
    def __init__(self, recipes_dir: Path | str):
        self._dir = Path(recipes_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _file(self, class_key: str) -> Path:
        return self._dir / _safe_name(class_key)

    def get(self, class_key: str) -> Recipe | None:
        f = self._file(class_key)
        if not f.exists():
            return None
        return _from_dict(json.loads(f.read_text()))

    def save(self, recipe: Recipe) -> None:
        self._file(recipe.class_key).write_text(
            json.dumps(_to_dict(recipe), indent=2, sort_keys=False)
        )

    def all(self) -> list[Recipe]:
        return [_from_dict(json.loads(f.read_text())) for f in sorted(self._dir.glob("*.json"))]


def _to_dict(r: Recipe) -> dict[str, Any]:
    return {
        "recipe_id": r.recipe_id,
        "class_key": r.class_key,
        "version": r.version,
        "plan": r.plan,
        "checks": r.checks,
        "history": r.history,
    }


def _from_dict(d: dict[str, Any]) -> Recipe:
    return Recipe(
        recipe_id=d["recipe_id"],
        class_key=d["class_key"],
        version=d["version"],
        plan=d["plan"],
        checks=d["checks"],
        history=d.get("history", []),
    )
