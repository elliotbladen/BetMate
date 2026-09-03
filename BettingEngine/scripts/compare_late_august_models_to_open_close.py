"""Compare the 27-30 August AFL/NRL pre-game models with open and close."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "BettingEngine/outputs/results"


def key(value: str) -> str:
    value = value.lower().replace("st. ", "st ")
    aliases = {"canterbury bankstown": "canterbury", "manly warringah": "manly",
               "st george illawarra": "st george",
               "north queensland": "north qld", "cronulla sutherland": "cronulla",
               "western bulldogs": "western bulldogs", "collingwood magpies": "collingwood"}
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    for source, target in aliases.items():
        value = value.replace(source, target)
    for suffix in (" broncos", " storm", " panthers", " bulldogs", " sea eagles",
                   " dragons", " cowboys", " tigers", " roosters", " rabbitohs",
                   " eels", " sharks", " warriors", " knights", " dolphins"):
        if value.endswith(suffix) and value != suffix.strip():
            value = value[:-len(suffix)].strip() or suffix.strip()
    return value


def no_vig(home: float, away: float) -> tuple[float, float]:
    raw_home, raw_away = 1 / home, 1 / away
    total = raw_home + raw_away
    return raw_home / total, raw_away / total


def build() -> pd.DataFrame:
    market = pd.concat([
        pd.read_csv(ROOT / "data/odds/weekends/2026-08-27/afl.csv"),
        pd.read_csv(ROOT / "data/odds/weekends/2026-08-27/nrl.csv"),
    ], ignore_index=True)
    nrl = pd.read_csv(ROOT / "BettingEngine/results/r27_pricing_2026.csv")
    models = []
    for row in nrl.to_dict("records"):
        models.append({"sport": "NRL", "home": row["home"], "away": row["away"],
                       "model_home_prob": 1 / row["fair_home_odds"],
                       "model_away_prob": 1 / row["fair_away_odds"],
                       "model_home_margin": row["final_margin"],
                       "model_total": row["final_total"], "model_source": "R27 internal / official R26"})
    models.extend([
        {"sport": "AFL", "home": "Western Bulldogs", "away": "Collingwood",
         "model_home_prob": .501, "model_away_prob": .499, "model_home_margin": -3.4,
         "model_total": 166.6, "model_source": "Wildcard production report (rules line/total, blended H2H)"},
        {"sport": "AFL", "home": "Melbourne", "away": "Carlton",
         "model_home_prob": .469, "model_away_prob": .531, "model_home_margin": 2.6,
         "model_total": 181.6, "model_source": "Wildcard production report (rules line/total, blended H2H)"},
    ])
    output = []
    for model in models:
        candidates = market[(market["Sport"] == model["sport"]) &
                            (market["Home Team"].map(key) == key(model["home"])) &
                            (market["Away Team"].map(key) == key(model["away"]))]
        if candidates.empty:
            raise ValueError(f"market match missing: {model['sport']} {model['home']} v {model['away']}")
        quote = candidates.iloc[0]
        open_home, open_away = no_vig(quote["Home Odds Open"], quote["Away Odds Open"])
        close_home, close_away = no_vig(quote["Home Odds Close"], quote["Away Odds Close"])
        home_open_edge = model["model_home_prob"] - open_home
        away_open_edge = model["model_away_prob"] - open_away
        side = "home" if home_open_edge >= away_open_edge else "away"
        selected_prob = model[f"model_{side}_prob"]
        selected_open = quote[f"{side.title()} Odds Open"]
        selected_close = quote[f"{side.title()} Odds Close"]
        side_won = ((quote["Home Score"] > quote["Away Score"]) if side == "home"
                    else (quote["Away Score"] > quote["Home Score"]))
        home_line_open, home_line_close = quote["Home Line Open"], quote["Home Line Close"]
        output.append({
            "sport": model["sport"], "date": quote["Date"], "home": quote["Home Team"],
            "away": quote["Away Team"], "model_side_at_open": quote[f"{side.title()} Team"],
            "model_side_probability": selected_prob,
            "open_side_odds": selected_open, "close_side_odds": selected_close,
            "open_no_vig_probability": open_home if side == "home" else open_away,
            "close_no_vig_probability": close_home if side == "home" else close_away,
            "model_edge_open_pp": 100 * (home_open_edge if side == "home" else away_open_edge),
            "model_edge_close_pp": 100 * (selected_prob - (close_home if side == "home" else close_away)),
            "model_ev_open_pct": 100 * (selected_prob * selected_open - 1),
            "model_ev_close_pct": 100 * (selected_prob * selected_close - 1),
            "price_clv_open_to_close_pct": 100 * (selected_open / selected_close - 1),
            "model_side_won": side_won,
            "flat_1u_pnl_at_open": selected_open - 1 if side_won else -1,
            "model_home_margin": model["model_home_margin"],
            "market_implied_home_margin_open": -home_line_open,
            "market_implied_home_margin_close": -home_line_close,
            "home_line_edge_open": model["model_home_margin"] + home_line_open,
            "home_line_edge_close": model["model_home_margin"] + home_line_close,
            "model_total": model["model_total"], "total_open": quote["Total Score Open"],
            "total_close": quote["Total Score Close"],
            "total_edge_open": model["model_total"] - quote["Total Score Open"],
            "total_edge_close": model["model_total"] - quote["Total Score Close"],
            "home_score": quote["Home Score"], "away_score": quote["Away Score"],
            "model_source": model["model_source"],
        })
    return pd.DataFrame(output).sort_values(["sport", "date", "home"])


def main() -> None:
    frame = build()
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "late_august_2026_model_vs_open_close.csv"
    frame.to_csv(csv_path, index=False)
    lines = ["# Late August 2026 — model versus opening and closing markets", "",
             "Price CLV is `opening odds / closing odds - 1` on the side the model preferred at opening. Positive means the model-aligned side shortened.", ""]
    for sport, group in frame.groupby("sport"):
        lines += [f"## {sport}", "", "| Match | Model side | Open → close | Edge open → close | Price CLV | Model margin | Market margin open → close | Model total | Total open → close |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for row in group.to_dict("records"):
            lines.append(f"| {row['home']} v {row['away']} | {row['model_side_at_open']} ({row['model_side_probability']:.1%}) | ${row['open_side_odds']:.2f} → ${row['close_side_odds']:.2f} | {row['model_edge_open_pp']:+.1f}pp → {row['model_edge_close_pp']:+.1f}pp | {row['price_clv_open_to_close_pct']:+.1f}% | {row['model_home_margin']:+.1f} | {row['market_implied_home_margin_open']:+.1f} → {row['market_implied_home_margin_close']:+.1f} | {row['model_total']:.1f} | {row['total_open']:.1f} → {row['total_close']:.1f} |")
        lines += ["", f"Model-side positive price CLV: {(group['price_clv_open_to_close_pct'] > 0).sum()}/{len(group)}; mean {group['price_clv_open_to_close_pct'].mean():+.1f}%.", ""]
        line_toward = ((group["model_home_margin"] - group["market_implied_home_margin_close"]).abs() <
                       (group["model_home_margin"] - group["market_implied_home_margin_open"]).abs()).sum()
        total_toward = ((group["model_total"] - group["total_close"]).abs() <
                        (group["model_total"] - group["total_open"]).abs()).sum()
        lines += [f"Model-side winners: {group['model_side_won'].sum()}/{len(group)}; flat 1-unit opening-price P/L {group['flat_1u_pnl_at_open'].sum():+.2f}u ({group['flat_1u_pnl_at_open'].mean():+.1%} ROI).",
                  f"Closing line moved closer to the model in {line_toward}/{len(group)} games; closing total moved closer in {total_toward}/{len(group)}.",
                  f"Margin MAE: {(group['home_score'] - group['away_score'] - group['model_home_margin']).abs().mean():.1f} points. Total MAE: {(group['home_score'] + group['away_score'] - group['model_total']).abs().mean():.1f} points.", ""]
        qualified = group[group["model_ev_open_pct"] >= 10]
        if not qualified.empty:
            lines += [f"At the proposed 10% opening-EV rule: {len(qualified)} qualifiers, {(qualified['price_clv_open_to_close_pct'] > 0).sum()}/{len(qualified)} positive CLV, mean CLV {qualified['price_clv_open_to_close_pct'].mean():+.1f}%, P/L {qualified['flat_1u_pnl_at_open'].sum():+.2f}u ({qualified['flat_1u_pnl_at_open'].mean():+.1%} ROI).", ""]
    (OUT / "late_august_2026_model_vs_open_close.md").write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
