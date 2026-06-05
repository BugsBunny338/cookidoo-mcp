#!/usr/bin/env python3
"""Register this server in Claude Desktop's config (cross-platform, idempotent).

Figures out the OS-correct claude_desktop_config.json location, backs it up, and
merges in a "cookidoo" entry pointing at *this* checkout's venv + server.py. Safe
to run repeatedly. No third-party deps, so it can run with the system Python too.

    python3 configure_claude.py            # add/update the entry
    python3 configure_claude.py --remove   # remove it
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
VENV_PYTHON = REPO / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")
SERVER = REPO / "server.py"


def config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "Claude/claude_desktop_config.json"
    return Path.home() / ".config/Claude/claude_desktop_config.json"


def main() -> int:
    remove = "--remove" in sys.argv
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    cfg: dict = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"! {path} is not valid JSON. Fix or remove it, then re-run.")
            return 1
        backup = path.with_name(path.name + f".bak.{int(time.time())}")
        shutil.copy(path, backup)
        print(f"  backed up existing config -> {backup.name}")

    servers = cfg.setdefault("mcpServers", {})
    if remove:
        servers.pop("cookidoo", None)
        print("  removed 'cookidoo' entry")
    else:
        if not VENV_PYTHON.exists():
            print(f"! venv Python not found at {VENV_PYTHON}. Run install.sh first.")
            return 1
        servers["cookidoo"] = {"command": str(VENV_PYTHON), "args": [str(SERVER)]}
        print(f"  set mcpServers.cookidoo -> {VENV_PYTHON}")

    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"✓ Updated {path}")
    print("  Restart Claude Desktop to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
