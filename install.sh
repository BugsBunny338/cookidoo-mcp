#!/usr/bin/env bash
#
# One-command installer for the Cookidoo MCP server.
# Sets up a venv, installs dependencies, optionally captures your Cookidoo login,
# and registers the server in Claude Desktop. Safe to re-run.
#
#   ./install.sh
#
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Cookidoo MCP installer"

# --- 1. Python 3.12+ -------------------------------------------------------- #
if ! command -v python3 >/dev/null 2>&1; then
  echo "! Python 3 not found. Install Python 3.12+ from https://www.python.org/downloads/ and re-run."
  exit 1
fi
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PYMAJOR=${PYV%%.*}; PYMINOR=${PYV##*.}
if [ "$PYMAJOR" -lt 3 ] || { [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 12 ]; }; then
  echo "! Python $PYV found, but 3.12+ is required. Please upgrade and re-run."
  exit 1
fi
echo "  Python $PYV OK"

# --- 2. venv + dependencies ------------------------------------------------- #
echo "==> Creating virtual environment and installing dependencies (this can take a minute)…"
python3 -m venv venv
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt
echo "  dependencies installed"

# --- 3. Credentials (optional) ---------------------------------------------- #
# Search and reading recipes need no login. Only "save to Thermomix" does.
if [ -f .env ]; then
  echo "  .env already present — leaving it as is"
else
  echo ""
  echo "Saving recipes to your Thermomix needs your Cookidoo login."
  echo "(Searching and reading recipes works without it.)"
  printf "Set up your Cookidoo login now? [y/N] "
  read -r ANS || ANS=""
  if [[ "$ANS" =~ ^[Yy] ]]; then
    printf "  Cookidoo email: "; read -r EMAIL
    printf "  Cookidoo password: "; read -rs PASSWORD; echo
    printf "  Account country code [us]: "; read -r COUNTRY; COUNTRY=${COUNTRY:-us}
    umask 077
    printf 'EMAIL=%s\nPASSWORD=%s\nCOOKIDOO_COUNTRY=%s\n' "$EMAIL" "$PASSWORD" "$COUNTRY" > .env
    echo "  wrote .env (gitignored)"
  else
    echo "  skipped — you can run ./install.sh again later to add it"
  fi
fi

# --- 4. Register with Claude Desktop ---------------------------------------- #
echo "==> Registering with Claude Desktop…"
./venv/bin/python configure_claude.py

# --- 5. Smoke test ---------------------------------------------------------- #
echo "==> Verifying the server loads…"
./venv/bin/python -c "import server; print('  server OK')"

echo ""
echo "✅ Done. Quit and reopen Claude Desktop, then ask it:"
echo '   "I have chicken, zucchini and cream — find me a Cookidoo recipe."'
