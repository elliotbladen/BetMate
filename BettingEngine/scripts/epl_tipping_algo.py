#!/usr/bin/env python3
"""Generate Baz's EPL tipping-comp card from an existing pricing CSV."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.football.tipping import PoolRules, tip_round


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pricing", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, default=ROOT / "outputs/football/epl/epl_1x2_confluence_matrix.xlsx")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/football/epl/latest_tipping_card.json")
    parser.add_argument("--correct-points", type=float, default=1.0)
    parser.add_argument("--draw-points", type=float)
    parser.add_argument("--leverage", type=float, default=0.0,
                        help="0 maximises expected points; use only with crowd ownership and pool-state support")
    args = parser.parse_args()
    rules = PoolRules(correct_points=args.correct_points, draw_points=args.draw_points, leverage=args.leverage)
    tips = tip_round(args.pricing, args.matrix, rules)
    payload = {"sport": "EPL", "market": "1X2", "rules": vars(rules), "tips": tips,
               "provisional": True,
               "provisional_reason": "Competition scoring rules and crowd ownership are not configured."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
