#!/usr/bin/env python3
"""Store a PunterEdge API key locally without echoing or committing it.

Run this directly in a terminal on the machine that runs the collector:
    python scripts/set_puntersedge_key.py
"""

from __future__ import annotations

import os
import tempfile
from getpass import getpass
from pathlib import Path


KEY_NAME = "PUNTERSEDGE_API_KEY"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env.puntersedge.local"


def main() -> None:
    api_key = getpass("Paste PunterEdge API key (input will be hidden): ").strip()
    if not api_key:
        raise SystemExit("No key entered; nothing was written.")

    existing_lines: list[str] = []
    if ENV_PATH.exists():
        existing_lines = [
            line
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines()
            if not line.startswith(f"{KEY_NAME}=")
        ]

    content = "\n".join([*existing_lines, f"{KEY_NAME}={api_key}", ""])
    fd, temp_name = tempfile.mkstemp(prefix=".puntersedge-", dir=ENV_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, ENV_PATH)
        os.chmod(ENV_PATH, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    print(f"Saved locally to {ENV_PATH.name} (permissions: owner read/write only).")
    print("The key was not printed and this file is ignored by Git.")


if __name__ == "__main__":
    main()
