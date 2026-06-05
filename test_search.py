"""Live integration test for the Cookidoo search client.

Run directly against the real Cookidoo API using the credentials in .env:

    ./venv/bin/python test_search.py
    ./venv/bin/python test_search.py chicken zucchini cream
    ./venv/bin/python test_search.py --language cs ku,curka cuketa

This is an *integration* test (it hits the network and needs a real account +
active subscription), not a unit test. It's the fastest way to confirm the
end-to-end flow before wiring up Claude Desktop.
"""

from __future__ import annotations

import argparse
import asyncio

from cookidoo_client import search_recipes_by_ingredients


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test Cookidoo ingredient search.")
    parser.add_argument("ingredients", nargs="*", default=["chicken", "zucchini"])
    parser.add_argument("--language", default=None, help="en, cs, pl, de ...")
    parser.add_argument("--query", default=None)
    parser.add_argument("--difficulty", default=None)
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()

    print(f"Searching for: {args.ingredients} (language={args.language})\n")
    recipes = await search_recipes_by_ingredients(
        args.ingredients,
        query=args.query,
        language=args.language,
        difficulty=args.difficulty,
        max_results=args.max_results,
    )
    if not recipes:
        print("No recipes found.")
        return
    for i, r in enumerate(recipes, 1):
        meta = []
        if r.total_time_min:
            meta.append(f"{r.total_time_min} min")
        if r.difficulty:
            meta.append(r.difficulty)
        suffix = f"  [{', '.join(meta)}]" if meta else ""
        print(f"{i}. {r.name}{suffix}\n   {r.url}")


if __name__ == "__main__":
    asyncio.run(main())
