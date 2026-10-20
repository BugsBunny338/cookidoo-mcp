# cookidoo-mcp

An [MCP](https://modelcontextprotocol.io) server for finding and cooking
[Cookidoo](https://cookidoo.com) (Thermomix) recipes from Claude. Tell Claude
what's in your fridge, read the full recipe with step-by-step Thermomix
instructions, and push it to your Thermomix — all without leaving the chat.

Runs locally as a stdio subprocess launched by Claude Desktop. No hosting needed.

## Demo

<!-- 📹 Drop a screen recording here once you have one. See assets/README.md.
     Then uncomment:  ![Fridge to Thermomix](assets/demo.gif)  -->

A typical fridge-to-Thermomix conversation in Claude Desktop:

> **You:** I've got chicken, zucchini and cream in the fridge — what can I make?
>
> **Claude:** *(search_recipes_by_ingredients)* Here are a few:
> 1. Creamy Asparagus, Potato and Leek Soup — 30 min, easy
> 2. Chicken with creamy vegetable sauce — 50 min, medium
> 3. Fruit Ice Cream — 5 min, easy
>
> **You:** Show me the soup.
>
> **Claude:** *(get_recipe)*
> **Creamy Asparagus, Potato and Leek Soup** · 30 min · serves 4
> *Ingredients:* 30 g olive oil · 120 g onions · 250 g leeks · 200 g potatoes · 400 g green asparagus · …
> *Steps:*
> 1. Place oil, onions, leeks and potatoes in mixing bowl then chop 5 sec/speed 5. Sauté 5 min/120°C/speed 1.
> 2. Add thyme, marjoram and asparagus then cook 6 min/100°C/speed 1. Blend 1 min/speed 9.
> 3. Add water, stock, salt, pepper then cook 10 min/100°C/speed 1. …
>
> **You:** Perfect, send it to my Thermomix.
>
> **Claude:** *(save_recipe_to_thermomix)* Saved to your "From Claude" collection on
> Cookidoo. Open My Recipes → Collections on your Thermomix to cook it.

## Tools

| Tool | What it does | Login? |
|------|--------------|--------|
| `search_recipes_by_ingredients` | Find recipes by ingredients (+ optional language, difficulty) | No |
| `get_recipe` | Full ingredients + step-by-step Thermomix instructions | No |
| `save_recipe_to_thermomix` | Save a recipe to your Cookidoo account so it shows on the device | **Yes** |

Search and recipe details are public, so **no credentials are needed to find and
read recipes**. Only saving a recipe to your account requires your Cookidoo login.

> **Note:** This builds on the unofficial, reverse-engineered
> [`cookidoo-api`](https://github.com/miaucl/cookidoo-api) library and is for
> personal use. Saving to your account needs an account with an active
> subscription. Requires Python 3.12+ (cookidoo-api 0.19).

## Install (one command)

```bash
git clone https://github.com/BugsBunny338/cookidoo-mcp.git
cd cookidoo-mcp
./install.sh
```

`install.sh` creates the environment, installs dependencies, optionally captures
your Cookidoo login, and **registers itself in Claude Desktop automatically**.
Then restart Claude Desktop. Full walkthrough (and Windows steps) in
**[INSTALL.md](INSTALL.md)**.

### Manual setup (if you prefer)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # only needed for save_recipe_to_thermomix
python configure_claude.py        # register with Claude Desktop
```

`.env` (optional — search works without it):

```
EMAIL=you@example.com
PASSWORD=your_cookidoo_password
COOKIDOO_COUNTRY=us               # your account's country code (lowercase)
```

## Try it (before wiring up Claude)

```bash
./venv/bin/python test_search.py chicken zucchini cream      # search (no login)
./venv/bin/python test_search.py --language cs kure cuketa   # Czech recipes
./venv/bin/python test_save.py r85110                        # save to account (login)
./venv/bin/python test_params.py                             # unit tests
```

## Wire up Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "cookidoo": {
      "command": "/absolute/path/to/cookidoo-mcp/venv/bin/python",
      "args": ["/absolute/path/to/cookidoo-mcp/server.py"],
      "env": {
        "EMAIL": "you@example.com",
        "PASSWORD": "your_cookidoo_password",
        "COOKIDOO_COUNTRY": "us"
      }
    }
  }
}
```

Restart Claude Desktop, then ask:
*"I have chicken, zucchini and cream — find me a Cookidoo recipe, show me the
steps, and save it to my Thermomix."*

## Multi-language

The account region (`COOKIDOO_COUNTRY`) sets the API endpoint; the `language`
argument on the search tool selects the recipe language per search (`en`, `cs`,
`pl`, `de`, …). Which languages a given account can reach depends on Cookidoo's
catalog for that region.

## How it's structured

- `cookidoo_client.py` — all Cookidoo logic (transport-agnostic; reusable from a
  CLI, tests, or a future HTTP/Cloud Run entrypoint).
- `server.py` — thin FastMCP adapter exposing the tools over stdio.
- `test_*.py` — live integration tests and deterministic unit tests.

`.env` and `.auth.json` (cached login tokens) are gitignored and must never be committed.

## Authors

See [AUTHORS.md](AUTHORS.md) — Jiří Zajíc and Petra Zajícová.

## License

MIT — see [LICENSE](LICENSE).
