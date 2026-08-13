#!/usr/bin/env python3
"""Publish current Baz context without requiring the HTTP service to be running.

The public chat reads the sanitised Supabase blob, while its source is local.
This helper lets the pricing workflow refresh that blob from the same context
functions used by ``baz_server.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
BETMATE_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
import baz_server  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "push_baz_context", BETMATE_ROOT / "scripts" / "push_baz_context.py"
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load push_baz_context.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def local_get_json(path: str):
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    sport = query.get("sport", ["NRL"])[0]
    if parsed.path == "/context/round":
        return baz_server.context_round(sport=sport)
    if parsed.path == "/signals":
        return baz_server.signals(sport=sport)
    if parsed.path == "/clv":
        return baz_server.clv(weeks=int(query.get("weeks", [4])[0]))
    if parsed.path == "/context/game":
        return baz_server.context_game(
            home=query["home"][0], away=query["away"][0], sport=sport
        )
    raise ValueError(f"Unsupported local Baz endpoint: {path}")


def main() -> None:
    publisher.load_env()
    publisher.get_json = local_get_json
    sports = [arg.upper() for arg in sys.argv[1:]] or ["NRL", "AFL"]
    for sport in sports:
        if sport not in {"NRL", "AFL"}:
            raise ValueError(f"Unsupported sport: {sport}")
        context = publisher.build_context(sport)
        publisher.push_context(sport, context)
        print(f"Published {sport} R{context['round']} ({len(context['round_context']['games'])} active games)")


if __name__ == "__main__":
    main()
