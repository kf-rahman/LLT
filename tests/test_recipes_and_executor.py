"""Feature #5 & #6 acceptance: recipe lookup/authoring and the executor."""

from __future__ import annotations

import pytest

from ingestor.executor import UnknownToolError, execute
from ingestor.models import Recipe, Signature
from ingestor.recipe_store import RecipeStore
from ingestor.recipes import DefaultRecipeAuthor, get_or_author, get_recipe
from ingestor.tools import build_default_registry


def test_get_recipe_hit_and_miss(tmp_path):
    store = RecipeStore(tmp_path / "r")
    assert get_recipe(store, "text") is None
    store.save(Recipe("text@1", "text", 1, [{"tool": "chunk"}], ["chunks > 0"]))
    assert get_recipe(store, "text").recipe_id == "text@1"


def test_author_on_miss_persists_and_is_idempotent(tmp_path):
    store = RecipeStore(tmp_path / "r")
    author = DefaultRecipeAuthor()
    sig = Signature(kind="text")

    recipe, authored = get_or_author(store, "text", sig, author)
    assert authored is True
    assert recipe.plan and recipe.checks  # non-empty plan + at least one check
    assert recipe.recipe_id == "text@1"
    assert get_recipe(store, "text") is not None  # persisted

    again, authored2 = get_or_author(store, "text", sig, author)
    assert authored2 is False  # second time is a hit, not a re-author
    assert again.recipe_id == recipe.recipe_id


def test_linear_plan_runs_and_produces_chunks(event_factory):
    recipe = Recipe("text@1", "text", 1,
                    [{"tool": "chunk", "by": "section"}, {"tool": "embed"}, {"tool": "store"}],
                    ["chunks > 0"])
    ev = event_factory("s://a.txt", b"para one\n\npara two")
    result = execute(recipe, ev, build_default_registry())
    assert result.error is None
    assert [c.content for c in result.chunks] == ["para one", "para two"]
    assert all(c.embedding is not None for c in result.chunks)  # embed ran


def test_route_step_dispatches_by_region(event_factory):
    recipe = Recipe("mix@1", "pdf__text+tables", 1,
                    [{"tool": "layout"},
                     {"route": {
                         "table": [{"tool": "extract_table"}],
                         "text": [{"tool": "chunk", "by": "section"}],
                     }}],
                    ["chunks > 0"])
    # A real tabular block: >=4 rows with a consistent 3-column shape (2+ spaces).
    data = (b"Intro narrative paragraph.\n\n"
            b"Item      Qty      Price\n"
            b"Apple     3        1.50\n"
            b"Pear      5        0.75\n"
            b"Plum      2        0.90\n\n"
            b"Closing narrative paragraph.")
    result = execute(recipe, event_factory("s://m.txt", data), build_default_registry())
    regions = {c.region for c in result.chunks}
    assert "table" in regions and "text" in regions
    assert result.facts["tables_extracted"] >= 4


def test_unknown_tool_is_reported_not_silent(event_factory):
    recipe = Recipe("x@1", "x", 1, [{"tool": "does_not_exist"}], ["chunks > 0"])
    result = execute(recipe, event_factory("s://a", b"data"), build_default_registry())
    assert result.error is not None and "does_not_exist" in result.error
