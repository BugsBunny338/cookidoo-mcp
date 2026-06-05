"""Live test for saving a recipe to the Cookidoo account (WRITES to the account).

Usage:
    ./venv/bin/python test_save.py r85110
    ./venv/bin/python test_save.py r85110 --collection "From Claude"

Adds the recipe to a custom collection (creating it if needed) and reads the
account's collections back to confirm the write persisted.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

logging.disable(logging.CRITICAL)

from cookidoo_client import cookidoo_session, save_recipe_to_account


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe_id")
    ap.add_argument("--collection", default="From Claude")
    args = ap.parse_args()

    print(f"Saving {args.recipe_id} -> '{args.collection}' ...")
    result = await save_recipe_to_account(args.recipe_id, collection_name=args.collection)
    print(
        f"  recipe_id={result.recipe_id} collection_created={result.collection_created} "
        f"already_present={result.already_present}"
    )

    print("\nReading account collections back to verify:")
    async with cookidoo_session(require_credentials=True) as c:
        await c.login()
        for col in await c.get_custom_collections():
            name = getattr(col, "name", None)
            n = getattr(col, "total_recipes", None)
            cid = getattr(col, "id", None)
            print(f"  - {name!r}  recipes={n}  id={cid}")


if __name__ == "__main__":
    asyncio.run(main())
