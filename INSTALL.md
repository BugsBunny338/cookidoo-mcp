# Installing the Cookidoo recipe tool in Claude Desktop

This adds three tools to Claude Desktop so you can ask for recipes by
ingredients, read full step-by-step Thermomix instructions, and save a recipe
to your Thermomix — all from a chat.

> **Reality check:** Claude Desktop on its own can't install software (it can't
> run commands on your computer). So installation is **one command you paste into
> Terminal**, which does everything automatically — including wiring itself into
> Claude Desktop. If you use Claude Code or Claude Desktop's local-agent mode,
> Claude *can* run that command for you (see "Let Claude do it" below).

## Prerequisites (one-time)

1. **Claude Desktop** — https://claude.ai/download
2. **Python 3.12 or newer** — https://www.python.org/downloads/
   (macOS: `python3 --version` to check.)

## Install (macOS / Linux)

Paste this into Terminal:

```bash
git clone https://github.com/BugsBunny338/cookidoo-mcp.git
cd cookidoo-mcp
./install.sh
```

`install.sh` will:
- create an isolated Python environment and install dependencies,
- optionally ask for your Cookidoo login (only needed to **save** recipes to the
  Thermomix — searching and reading work without it),
- register itself in Claude Desktop's config automatically (with a backup),
- run a quick check that it loads.

Then **quit and reopen Claude Desktop**. Ask it:

> *"I have chicken, zucchini and cream — find me a Cookidoo recipe, show me the
> steps, and save it to my Thermomix."*

That's it.

## Let Claude do it for you

If you have **Claude Code** or Claude Desktop **local-agent mode** enabled, you
can skip Terminal and just tell Claude:

> *"Clone https://github.com/BugsBunny338/cookidoo-mcp and run its install.sh,
> then tell me to restart Claude Desktop."*

Claude will run the same steps. (Plain Claude Desktop without local-agent mode
can't do this — use the Terminal command above.)

## Re-running / changing your login

`./install.sh` is safe to run again. To add or change your Cookidoo login later,
delete `.env` and re-run it, or edit `.env` directly.

## Uninstall

```bash
./venv/bin/python configure_claude.py --remove   # unregister from Claude Desktop
```

Then delete the `cookidoo-mcp` folder.

## Windows

Automated `install.sh` targets macOS/Linux. On Windows, do it manually:

```powershell
git clone https://github.com/BugsBunny338/cookidoo-mcp.git
cd cookidoo-mcp
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env          # then edit .env (only needed for saving recipes)
venv\Scripts\python configure_claude.py
```

Restart Claude Desktop.

## Troubleshooting

- **Tools don't appear:** fully quit Claude Desktop (not just close the window)
  and reopen. Confirm the `cookidoo` entry exists in
  `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).
- **"This action needs your Cookidoo login":** you tried to save a recipe without
  credentials. Re-run `./install.sh` and provide your login, or add `EMAIL` /
  `PASSWORD` to `.env`.
- **Saving fails / wrong catalog:** set `COOKIDOO_COUNTRY` in `.env` to your
  account's country code (e.g. `us`, `cz`, `de`).
