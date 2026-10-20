"""Deterministic unit tests for search-param encoding (no network).

Root-cause regression test: the upstream cookidoo-api joins list params with a
comma (``ingredients=chicken,zucchini``), which the Cookidoo API reads as a
single ingredient literally named "chicken,zucchini" and returns zero results.
The API actually wants repeated params (``ingredients=chicken&ingredients=zucchini``).
These tests pin the correct repeated-param encoding.

Run: ./venv/bin/python -m pytest test_params.py   (or just exec it)
"""

from __future__ import annotations

from types import SimpleNamespace

from cookidoo_client import _collection_recipe_ids, build_search_pairs


def test_multiple_ingredients_are_repeated_not_comma_joined():
    pairs = build_search_pairs(ingredients=["chicken", "zucchini", "cream"])
    ingredient_values = [v for k, v in pairs if k == "ingredients"]
    assert ingredient_values == ["chicken", "zucchini", "cream"]
    # The broken behavior would instead produce a single comma-joined value:
    assert "chicken,zucchini,cream" not in ingredient_values


def test_single_ingredient():
    pairs = build_search_pairs(ingredients=["chicken"])
    assert [v for k, v in pairs if k == "ingredients"] == ["chicken"]


def test_optional_params_included_and_named_for_api():
    pairs = build_search_pairs(
        ingredients=["egg"],
        query="omelette",
        exclude_ingredients=["milk"],
        languages=["en", "cs"],
        difficulty="easy",
        limit=5,
    )
    d = {}
    for k, v in pairs:
        d.setdefault(k, []).append(v)
    assert d["query"] == ["omelette"]
    assert d["excludeIngredients"] == ["milk"]
    assert d["languages"] == ["en", "cs"]  # repeated, not "en,cs"
    assert d["difficulty"] == ["easy"]
    assert d["limit"] == ["5"]  # the API ignores pageSize


def test_empty_inputs_produce_no_pairs():
    assert build_search_pairs() == []
    assert build_search_pairs(ingredients=[]) == []


def test_collection_recipe_ids_reads_chapters():
    # Recipes live under chapters[].recipes[], not a flat .recipes field.
    collection = SimpleNamespace(
        chapters=[
            SimpleNamespace(recipes=[SimpleNamespace(id="r1"), SimpleNamespace(id="r2")]),
            SimpleNamespace(recipes=[SimpleNamespace(id="r3")]),
        ]
    )
    assert _collection_recipe_ids(collection) == {"r1", "r2", "r3"}


def test_collection_recipe_ids_empty_collection():
    assert _collection_recipe_ids(SimpleNamespace(chapters=[])) == set()
    assert _collection_recipe_ids(SimpleNamespace()) == set()


if __name__ == "__main__":
    import sys, traceback

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError:
                failures += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    sys.exit(1 if failures else 0)
