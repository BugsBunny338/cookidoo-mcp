"""Transport-agnostic Cookidoo client.

All Cookidoo logic lives here so the MCP server (server.py) stays a thin adapter.
This module knows nothing about MCP -- it can be reused from a CLI, a test
script, or a future HTTP/Cloud Run entrypoint without changes.

Auth model (verified empirically against the API):
  * Search and recipe details (incl. full cooking steps) are PUBLIC -- no login,
    no credentials. Anonymous and authenticated searches return identical results.
  * Writing to the user's account (so a recipe shows up on their Thermomix) DOES
    require login. Only that path needs EMAIL/PASSWORD.
"""

from __future__ import annotations

import html as _html
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

import aiohttp

try:
    # Best-effort: load .env for local runs (CLI/tests). Claude Desktop instead
    # passes env vars via the config 'env' block, so dotenv is optional.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

from cookidoo_api import (
    Cookidoo,
    CookidooAuthException,
    CookidooConfig,
    CookidooSearchResult,
    get_localization_options,
)
from cookidoo_api.const import RECIPE_PATH
from cookidoo_api.helpers import cookidoo_search_result_from_json

# Cache for the authenticated session cookies (only used by account-write paths).
COOKIE_FILE = Path(__file__).resolve().parent / ".cookies"


# --------------------------------------------------------------------------- #
# Data shapes returned to the MCP layer
# --------------------------------------------------------------------------- #
@dataclass
class RecipeResult:
    """A single search hit, ready to show the user."""

    id: str
    name: str
    url: str
    difficulty: str | None = None
    total_time_min: int | None = None
    active_time_min: int | None = None


@dataclass
class RecipeStepGroup:
    title: str
    steps: list[str]


@dataclass
class SaveResult:
    """Outcome of saving a recipe into the user's account."""

    recipe_id: str
    collection_name: str
    collection_created: bool
    already_present: bool


@dataclass
class RecipeFull:
    """A complete recipe: enough for the user to actually cook it."""

    id: str
    name: str
    url: str
    difficulty: str | None
    total_time_min: int | None
    active_time_min: int | None
    servings: int | None
    ingredients: list[str] = field(default_factory=list)
    utensils: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    step_groups: list[RecipeStepGroup] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Config / session
# --------------------------------------------------------------------------- #
def _read_env() -> tuple[str, str, str]:
    email = os.environ.get("EMAIL", "").strip()
    password = os.environ.get("PASSWORD", "").strip()
    # Petra's account is US; the country selects which Cookidoo endpoint/catalog
    # we query. Auth is NOT required for search.
    country = os.environ.get("COOKIDOO_COUNTRY", "us").strip().lower()
    return email, password, country


async def _build_config(*, require_credentials: bool = False) -> CookidooConfig:
    email, password, country = _read_env()
    if require_credentials and (not email or not password):
        raise RuntimeError(
            "This action needs your Cookidoo login. Set EMAIL and PASSWORD in the "
            ".env file (copy .env.example) or in claude_desktop_config.json's 'env' "
            "block. (Search does not need credentials -- only saving recipes to your "
            "account does.)"
        )
    options = await get_localization_options(country=country)
    if not options:
        raise RuntimeError(
            f"No Cookidoo localization found for country '{country}'. Set "
            "COOKIDOO_COUNTRY to your account's country code (e.g. 'us')."
        )
    return CookidooConfig(email=email, password=password, localization=options[0])


@asynccontextmanager
async def cookidoo_session(
    *, require_credentials: bool = False
) -> AsyncIterator[Cookidoo]:
    """Yield a Cookidoo client on a fresh aiohttp session.

    CookieJar(unsafe=True) is required for the cross-domain OAuth2 login flow used
    by account-write paths; it's harmless for anonymous reads.
    """
    cfg = await _build_config(require_credentials=require_credentials)
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        yield Cookidoo(session, cfg=cfg)


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
def build_search_pairs(
    *,
    query: str | None = None,
    ingredients: list[str] | None = None,
    exclude_ingredients: list[str] | None = None,
    languages: list[str] | None = None,
    difficulty: str | None = None,
    page_size: int | None = None,
    tmv: str | None = None,
) -> list[tuple[str, str]]:
    """Build search query params as a list of (key, value) pairs.

    List filters become REPEATED params (``ingredients=a&ingredients=b``). This is
    the whole point of bypassing cookidoo-api's ``search_recipes``, which instead
    comma-joins list values (``ingredients=a,b``) -- the Cookidoo API reads that as
    one ingredient literally named "a,b" and returns nothing. Keys match the API's
    expected names (e.g. camelCase ``excludeIngredients``, ``pageSize``).
    """
    pairs: list[tuple[str, str]] = []
    if query:
        pairs.append(("query", query))
    for ing in ingredients or []:
        if ing and ing.strip():
            pairs.append(("ingredients", ing.strip()))
    for ing in exclude_ingredients or []:
        if ing and ing.strip():
            pairs.append(("excludeIngredients", ing.strip()))
    for lang in languages or []:
        if lang and lang.strip():
            pairs.append(("languages", lang.strip()))
    if difficulty:
        pairs.append(("difficulty", difficulty))
    if page_size:
        pairs.append(("pageSize", str(page_size)))
    if tmv:
        pairs.append(("tmv", tmv))
    return pairs


async def _raw_search(
    client: Cookidoo, *, locale: str, pairs: list[tuple[str, str]]
) -> CookidooSearchResult:
    """Run a search via repeated params, reusing the client's headers + parser.

    Goes through the library's ``_request_json`` (so headers and error wrapping
    apply) but pre-builds the URL query so list params are repeated rather than
    comma-joined. Touches a couple of private attributes; acceptable because we
    pin cookidoo-api to a specific git commit.
    """
    url = (client.api_endpoint / "search" / locale).with_query(pairs)
    result = await client._request_json("get", url, "search recipes")
    if not isinstance(result, dict):
        return CookidooSearchResult(recipes=[], total=0)
    return cookidoo_search_result_from_json(result, client._cfg.localization)


def _to_minutes(seconds: int | None) -> int | None:
    if not seconds or seconds <= 0:
        return None
    return round(seconds / 60)


async def search_recipes_by_ingredients(
    ingredients: list[str],
    *,
    query: str | None = None,
    language: str | None = None,
    difficulty: str | None = None,
    max_results: int = 5,
    enrich: bool = True,
) -> list[RecipeResult]:
    """Search Cookidoo by ingredients (anonymous -- no login needed).

    Parameters
    ----------
    ingredients
        Ingredients to search for, e.g. ["chicken", "zucchini", "cream"].
    query
        Optional free-text query in addition to the ingredients.
    language
        Optional recipe language code, e.g. "en", "cs", "pl", "de". Maps to the
        search locale and language filter. If None, the account's default is used.
    difficulty
        Optional difficulty filter: "easy", "medium", or "hard".
    max_results
        Maximum recipes to return (default 5). Each result costs one extra detail
        call when enrich=True, so this is kept small.
    enrich
        When True (default), fetch per-recipe details to populate difficulty and
        cooking times -- the search hit itself carries only name + URL.
    """
    async with cookidoo_session() as client:
        locale = language or client._cfg.localization.language.split("-")[0]
        pairs = build_search_pairs(
            query=query,
            ingredients=ingredients,
            languages=[language] if language else None,
            difficulty=difficulty,
            page_size=max_results,
        )
        result = await _raw_search(client, locale=locale, pairs=pairs)

        recipes: list[RecipeResult] = []
        for hit in result.recipes[:max_results]:
            rec = RecipeResult(id=hit.id, name=hit.name, url=hit.url)
            if enrich:
                try:
                    d = await client.get_recipe_details(hit.id)
                    rec.difficulty = getattr(d, "difficulty", None) or None
                    rec.total_time_min = _to_minutes(getattr(d, "total_time", None))
                    rec.active_time_min = _to_minutes(getattr(d, "active_time", None))
                except Exception:
                    # One bad detail fetch must not sink the whole search.
                    pass
            recipes.append(rec)
        return recipes


# --------------------------------------------------------------------------- #
# Full recipe (ingredients + cooking steps) -- anonymous
# --------------------------------------------------------------------------- #
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    """Strip HTML tags (<nobr>, <strong>, ...) and unescape entities.

    Tag *contents* are kept, so Thermomix settings like "5 sec/speed 5" survive.
    """
    return _html.unescape(_TAG_RE.sub("", text or "")).strip()


def _format_ingredient(ri: dict) -> str:
    qty = (ri.get("quantity") or {}).get("value")
    unit = (ri.get("unitNotation") or "").strip()
    name = (ri.get("ingredientNotation") or "").strip()
    prep = (ri.get("preparation") or "").strip()
    qty_str = f"{qty:g}" if isinstance(qty, (int, float)) and qty else ""
    amount = " ".join(p for p in (qty_str, unit) if p)
    line = f"{amount} {name}".strip() if amount else name
    if prep:
        line = f"{line}, {prep}"
    if ri.get("optional"):
        line = f"{line} (optional)"
    return _clean(line)


def _time_value(times: list[dict], type_: str) -> int | None:
    for t in times or []:
        if t.get("type") == type_:
            return (t.get("quantity") or {}).get("value")
    return None


async def get_full_recipe(recipe_id: str, *, language: str | None = None) -> RecipeFull:
    """Fetch a complete recipe (ingredients + step-by-step instructions).

    Anonymous: no login required. ``language`` is the locale URL segment; defaults
    to the account localization (recipe content comes back in the recipe's own
    language regardless).
    """
    async with cookidoo_session() as client:
        lang = language or client._cfg.localization.language
        url = client.api_endpoint / RECIPE_PATH.format(language=lang, id=recipe_id)
        raw = await client._request_json("get", url, "recipe details")
        if not isinstance(raw, dict) or not raw.get("title"):
            raise RuntimeError(f"Recipe '{recipe_id}' not found.")

        ingredients: list[str] = []
        for group in raw.get("recipeIngredientGroups", []):
            for ri in group.get("recipeIngredients", []):
                line = _format_ingredient(ri)
                if line:
                    ingredients.append(line)

        step_groups: list[RecipeStepGroup] = []
        for group in raw.get("recipeStepGroups", []):
            steps = [
                _clean(s.get("formattedText") or s.get("text"))
                for s in group.get("recipeSteps", [])
            ]
            steps = [s for s in steps if s]
            if steps:
                step_groups.append(
                    RecipeStepGroup(title=_clean(group.get("title")), steps=steps)
                )

        serving = (raw.get("servingSize") or {}).get("quantity", {}).get("value")
        times = raw.get("times", [])
        web_url = str(
            client.api_endpoint
            / RECIPE_PATH.format(
                language=client._cfg.localization.language, id=recipe_id
            )
        )
        return RecipeFull(
            id=recipe_id,
            name=_clean(raw.get("title")),
            url=web_url,
            difficulty=raw.get("difficulty") or None,
            total_time_min=_to_minutes(_time_value(times, "totalTime")),
            active_time_min=_to_minutes(_time_value(times, "activeTime")),
            servings=int(serving) if isinstance(serving, (int, float)) else None,
            ingredients=ingredients,
            utensils=[
                _clean(u.get("utensilNotation"))
                for u in raw.get("recipeUtensils", [])
                if _clean(u.get("utensilNotation"))
            ],
            tips=[
                _clean(ai.get("content"))
                for ai in raw.get("additionalInformation", [])
                if _clean(ai.get("content"))
            ],
            step_groups=step_groups,
        )


# --------------------------------------------------------------------------- #
# Account write: save a recipe so it shows up on the Thermomix (requires login)
# --------------------------------------------------------------------------- #
DEFAULT_COLLECTION = "From Claude"


async def _ensure_login(client: Cookidoo) -> None:
    """Make the client authenticated, reusing cached cookies when possible."""
    if COOKIE_FILE.exists():
        try:
            client.load_cookies(COOKIE_FILE)
        except Exception:
            pass
    if not getattr(client, "_logged_in", False):
        await client.login()
        try:
            client.save_cookies(COOKIE_FILE)
        except Exception:
            pass


def _collection_recipe_ids(collection: object) -> set[str]:
    """Recipe ids already in a custom collection.

    A CookidooCollection holds recipes under ``chapters[].recipes[]`` (there is no
    flat ``recipes`` field), so traverse the chapters.
    """
    ids: set[str] = set()
    for chapter in getattr(collection, "chapters", None) or []:
        for r in getattr(chapter, "recipes", None) or []:
            rid = getattr(r, "id", None)
            if rid:
                ids.add(rid)
    return ids


async def save_recipe_to_account(
    recipe_id: str, *, collection_name: str = DEFAULT_COLLECTION
) -> SaveResult:
    """Add a recipe to a custom collection in the user's Cookidoo account.

    The collection (default "From Claude") is created if it doesn't exist. On the
    Thermomix it appears under My Recipes -> Collections. Requires login.
    """
    async with cookidoo_session(require_credentials=True) as client:

        async def op() -> SaveResult:
            collections = await client.get_custom_collections()
            existing = next(
                (c for c in collections if (getattr(c, "name", "") or "").strip() == collection_name),
                None,
            )
            created = existing is None
            collection = existing or await client.add_custom_collection(collection_name)
            already = recipe_id in _collection_recipe_ids(collection)
            if not already:
                await client.add_recipes_to_custom_collection(collection.id, [recipe_id])
            return SaveResult(
                recipe_id=recipe_id,
                collection_name=collection_name,
                collection_created=created,
                already_present=already,
            )

        await _ensure_login(client)
        try:
            return await op()
        except CookidooAuthException:
            # Cached cookies expired -- log in fresh and retry once.
            await client.login()
            try:
                client.save_cookies(COOKIE_FILE)
            except Exception:
                pass
            return await op()
