"""Cookidoo MCP server.

A minimal MCP server for finding and reading Cookidoo (Thermomix) recipes. Runs
locally as a stdio subprocess launched by Claude Desktop. All real logic lives in
cookidoo_client.py; this file is just the MCP adapter so it can later be swapped
for an HTTP/Cloud Run entrypoint.

Tools:
  * search_recipes_by_ingredients -- find recipes by what's in the fridge (anon).
  * get_recipe                    -- full ingredients + cooking steps (anon).
"""

from __future__ import annotations

from fastmcp import FastMCP

from cookidoo_client import DEFAULT_COLLECTION, RecipeFull, RecipeResult, SaveResult
from cookidoo_client import get_full_recipe as _client_get_recipe
from cookidoo_client import save_recipe_to_account as _client_save
from cookidoo_client import search_recipes_by_ingredients as _client_search

mcp = FastMCP("cookidoo")


def _format_results(recipes: list[RecipeResult]) -> str:
    if not recipes:
        return (
            "No Cookidoo recipes matched those ingredients. Try fewer or more "
            "common ingredients, or a different language."
        )
    lines: list[str] = []
    for i, r in enumerate(recipes, 1):
        bits: list[str] = []
        if r.total_time_min:
            bits.append(f"{r.total_time_min} min total")
        if r.active_time_min:
            bits.append(f"{r.active_time_min} min hands-on")
        if r.difficulty:
            bits.append(r.difficulty)
        meta = f" ({', '.join(bits)})" if bits else ""
        lines.append(f"{i}. {r.name}{meta}\n   id: {r.id}  |  {r.url}")
    lines.append(
        "\nTo show full ingredients and steps for one, call get_recipe with its id."
    )
    return "\n".join(lines)


def _format_recipe(r: RecipeFull) -> str:
    out: list[str] = [f"# {r.name}"]
    meta: list[str] = []
    if r.total_time_min:
        meta.append(f"{r.total_time_min} min total")
    if r.active_time_min:
        meta.append(f"{r.active_time_min} min hands-on")
    if r.difficulty:
        meta.append(r.difficulty)
    if r.servings:
        meta.append(f"serves {r.servings}")
    if meta:
        out.append(" · ".join(meta))
    out.append(r.url)

    if r.ingredients:
        out.append("\n## Ingredients")
        out.extend(f"- {x}" for x in r.ingredients)
    if r.utensils:
        out.append("\n## Equipment")
        out.extend(f"- {x}" for x in r.utensils)

    out.append("\n## Steps")
    if len(r.step_groups) == 1 and not r.step_groups[0].title:
        for i, s in enumerate(r.step_groups[0].steps, 1):
            out.append(f"{i}. {s}")
    else:
        for g in r.step_groups:
            if g.title:
                out.append(f"\n### {g.title}")
            for i, s in enumerate(g.steps, 1):
                out.append(f"{i}. {s}")

    if r.tips:
        out.append("\n## Tips")
        out.extend(f"- {x}" for x in r.tips)
    return "\n".join(out)


@mcp.tool
async def search_recipes_by_ingredients(
    ingredients: list[str],
    query: str | None = None,
    language: str | None = None,
    difficulty: str | None = None,
    max_results: int = 5,
) -> str:
    """Find Cookidoo (Thermomix) recipes that use the given ingredients.

    Use this when the user describes what they have in their fridge/pantry and
    wants recipe ideas. Returns candidates with a recipe id; call get_recipe with
    an id to get full ingredients and cooking steps.

    Args:
        ingredients: Ingredients to cook with, e.g. ["chicken", "zucchini", "cream"].
        query: Optional extra free-text query (e.g. "soup", "quick dinner").
        language: Optional recipe language code: "en", "cs", "pl", "de", etc. Set
            this when the user asks for recipes in a specific language.
        difficulty: Optional filter: "easy", "medium", or "hard".
        max_results: Max recipes to return (default 5).
    """
    recipes = await _client_search(
        ingredients,
        query=query,
        language=language,
        difficulty=difficulty,
        max_results=max_results,
    )
    return _format_results(recipes)


@mcp.tool
async def get_recipe(recipe_id: str, language: str | None = None) -> str:
    """Get a full Cookidoo recipe: ingredients and step-by-step Thermomix instructions.

    Use this after search_recipes_by_ingredients, passing a recipe id from the
    results, when the user wants to actually cook a specific recipe.

    Args:
        recipe_id: The recipe id (e.g. "r725883"), as returned by the search tool.
        language: Optional locale segment (e.g. "cs", "en-US"). Usually unnecessary.
    """
    recipe = await _client_get_recipe(recipe_id, language=language)
    return _format_recipe(recipe)


@mcp.tool
async def save_recipe_to_thermomix(
    recipe_id: str, collection_name: str = DEFAULT_COLLECTION
) -> str:
    """Save a recipe to the user's Cookidoo account so it appears on the Thermomix.

    Adds the recipe to a custom collection (default "From Claude"), which shows up
    on the Thermomix under My Recipes -> Collections. Requires the user's Cookidoo
    login (EMAIL/PASSWORD). Use when the user wants to cook a recipe on their
    actual Thermomix device.

    Args:
        recipe_id: The recipe id (e.g. "r725883") from the search tool.
        collection_name: Collection to add it to (default "From Claude").
    """
    r: SaveResult = await _client_save(recipe_id, collection_name=collection_name)
    if r.already_present:
        return f'"{r.recipe_id}" is already in your "{r.collection_name}" collection on Cookidoo.'
    where = "new collection" if r.collection_created else "collection"
    return (
        f'Saved to your "{r.collection_name}" {where} on Cookidoo. '
        "Open My Recipes → Collections on your Thermomix to cook it."
    )


if __name__ == "__main__":
    mcp.run()
