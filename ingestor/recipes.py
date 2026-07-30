"""Recipe lookup and authoring.

Hot path: get_recipe(class_key) is an exact keyed lookup — a HIT runs
deterministically with no LLM. Miss path: a RecipeAuthor authors a recipe ONCE
for the novel class, which is then saved and reused forever.

v1 ships DefaultRecipeAuthor — a deterministic stub mapping known classes to a
sensible plan + checks. The RecipeAuthor Protocol is the seam where a real
LLM-backed author drops in without changing callers (the orchestrator).
"""

from __future__ import annotations

from typing import Protocol

from .models import Recipe, Signature
from .recipe_store import RecipeStore


def get_recipe(store: RecipeStore, class_key: str) -> Recipe | None:
    """Exact keyed lookup — the steady-state hot path."""
    return store.get(class_key)


def similar_recipes(store: RecipeStore, signature: Signature, k: int = 3) -> list[Recipe]:
    """Nearest prior recipes, to give a future LLM author few-shot examples.

    v1: naive — same-kind recipes. A real impl embeds the signature and does a
    vector search over recipe descriptions. Returns [] if nothing comparable.
    """
    return [r for r in store.all() if r.class_key.split("__")[0].split("-")[-1] == signature.kind][:k]


class RecipeAuthor(Protocol):
    def author(self, class_key: str, signature: Signature, similar: list[Recipe]) -> Recipe:
        ...


# Default plans per class. A plan is a list of steps; a step is either a tool
# step {"tool": name, ...params} or a route step {"route": {region: [steps]}}.
_DEFAULT_PLANS: dict[str, tuple[list[dict], list[str]]] = {
    "scanned-pdf": (
        [
            {"tool": "ocr"},
            {"tool": "chunk", "by": "page"},
            {"tool": "embed"},
            {"tool": "store"},
        ],
        ["chunks > 0", "text_nonempty"],
    ),
    "pdf__text": (
        [
            {"tool": "extract_text"},
            {"tool": "chunk", "by": "section"},
            {"tool": "embed"},
            {"tool": "store"},
        ],
        ["chunks > 0", "text_nonempty"],
    ),
    "pdf__text+tables": (
        [
            {"tool": "layout"},
            {"route": {
                "table": [{"tool": "extract_table"}, {"tool": "store"}],
                "text": [{"tool": "chunk", "by": "section"}, {"tool": "embed"}, {"tool": "store"}],
            }},
        ],
        # Text is the completeness bar; tables are a bonus, not a gate (a
        # mostly-text doc must not fail just because it has no real table).
        ["chunks > 0", "text_nonempty"],
    ),
    "csv": (
        [{"tool": "parse_csv"}, {"tool": "store"}],
        ["chunks > 0"],
    ),
    "image": (
        [{"tool": "ocr"}, {"tool": "chunk", "by": "page"}, {"tool": "embed"}, {"tool": "store"}],
        ["chunks > 0"],
    ),
    "text": (
        [{"tool": "chunk", "by": "section"}, {"tool": "embed"}, {"tool": "store"}],
        ["chunks > 0", "text_nonempty"],
    ),
    "html": (
        [{"tool": "extract_html"}, {"tool": "chunk", "by": "section"},
         {"tool": "embed"}, {"tool": "store"}],
        ["chunks > 0", "text_nonempty"],
    ),
}

# Fallback for any class we don't have a template for (also what a real LLM
# author would replace with a reasoned plan).
_FALLBACK_PLAN: tuple[list[dict], list[str]] = (
    [{"tool": "extract_text"}, {"tool": "chunk", "by": "section"}, {"tool": "embed"}, {"tool": "store"}],
    ["chunks > 0"],
)


class DefaultRecipeAuthor:
    """Deterministic stub author. Never calls an LLM; picks a template by class."""

    def author(self, class_key: str, signature: Signature, similar: list[Recipe]) -> Recipe:
        plan, checks = _DEFAULT_PLANS.get(class_key, _FALLBACK_PLAN)
        version = 1
        return Recipe(
            recipe_id=Recipe.make_id(class_key, version),
            class_key=class_key,
            version=version,
            plan=[dict(step) for step in plan],
            checks=list(checks),
        )


def get_or_author(
    store: RecipeStore,
    class_key: str,
    signature: Signature,
    author: RecipeAuthor,
) -> tuple[Recipe, bool]:
    """Return (recipe, authored). authored=True means the agent ran (a miss)."""
    existing = get_recipe(store, class_key)
    if existing is not None:
        return existing, False
    recipe = author.author(class_key, signature, similar_recipes(store, signature))
    store.save(recipe)
    return recipe, True
