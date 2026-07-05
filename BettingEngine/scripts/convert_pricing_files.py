"""
convert_pricing_files.py
------------------------
Converts all pricing txt files to CSV and copies/renames all pricing CSVs
into a clean, consistent folder structure:

  data/pricing/nrl/  NRL_PRICING_R{rr}_{week_ending}[_suffix].csv
  data/pricing/afl/  AFL_PRICING_R{rr}_{week_ending}[_suffix].csv

Source files handled:
  results/r9_pricing_2026.csv          → NRL_PRICING_R09_2026-04-28.csv
  results/r10_pricing_2026.csv         → NRL_PRICING_R10_2026-05-05.csv
  results/r11_pricing_2026.csv         → NRL_PRICING_R11_2026-05-12.csv
  results/r12_pricing_2026.csv         → NRL_PRICING_R12_2026-05-25.csv
  results/r9_2026_tier_breakdown.txt   → NRL_PRICING_R09_2026-04-28_tier_breakdown.csv
  data/clv/nrl/*_ml_shadow.txt         → NRL_PRICING_R{rr}_{date}_ml_shadow.csv
  results/r7_afl_2026.txt              → AFL_PRICING_R07_2026-04-28.csv
  results/r7_afl_2026_t1t2t3t4.txt    → AFL_PRICING_R07_2026-04-28_t1t2t3t4.csv
  results/r8_afl_2026.txt              → AFL_PRICING_R08_2026-05-05.csv
  outputs/afl_round_prep/r9_2026/afl_r9_pricing_2026.csv → AFL_PRICING_R09_2026-05-12.csv
  results/r11_afl_2026.csv             → AFL_PRICING_R11_2026-05-25.csv

Usage:
  uv run python scripts/convert_pricing_files.py
"""

import csv
import re
import shutil
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
OUT_NRL = ROOT / "data" / "pricing" / "nrl"
OUT_AFL = ROOT / "data" / "pricing" / "afl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_row(line: str) -> list[str]:
    """Split a fixed-width text table row on 2+ spaces."""
    return [c.strip() for c in re.split(r"\s{2,}", line.strip()) if c.strip()]


def clean_val(v: str) -> str:
    """Strip trailing flag/arrow characters from a value."""
    return re.sub(r"[▼▲⚑◆⚡]+$", "", v).strip()


def copy_csv(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  Copied:   {src.name} -> {dst.name}")


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        print(f"  No rows — skipping {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  Converted: {path.name} ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _data_blocks(text: str) -> list[list[str]]:
    """
    Return blocks of data lines between horizontal rule (───) separators.
    Each block is a list of non-empty stripped lines.
    """
    blocks, current = [], []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[─\-]{10,}", stripped):
            if current:
                blocks.append(current)
                current = []
            in_block = True
        elif in_block and stripped and not stripped.startswith("="):
            current.append(stripped)
    if current:
        blocks.append(current)
    return blocks


def parse_nrl_tier_breakdown(path: Path, round_num: int, week_ending: str) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    blocks = _data_blocks(text)

    # Block 0 = HANDICAP table rows
    # Block 1 = TOTALS table rows
    hcap_rows: dict[str, dict] = {}
    total_rows: dict[str, dict] = {}

    if len(blocks) >= 1:
        for line in blocks[0]:
            parts = split_row(line)
            if len(parts) < 8:
                continue
            game = parts[0]
            hcap_rows[game] = {
                "t1_hcap":    clean_val(parts[1]),
                "t2_hcap":    clean_val(parts[2]),
                "t3_hcap":    clean_val(parts[3]),
                "t4_hcap":    clean_val(parts[4]),
                "t5_hcap":    clean_val(parts[5]),
                "t6_hcap":    clean_val(parts[6]),
                "t7_hcap":    clean_val(parts[7]) if len(parts) > 7 else "",
                "final_margin": clean_val(parts[8]) if len(parts) > 8 else "",
                "hcap_line":  clean_val(parts[9]) if len(parts) > 9 else "",
                "home_win_pct": clean_val(parts[10]).rstrip("%") if len(parts) > 10 else "",
                "home_fair_odds": clean_val(parts[11]) if len(parts) > 11 else "",
                "away_fair_odds": clean_val(parts[12]) if len(parts) > 12 else "",
            }

    if len(blocks) >= 2:
        for line in blocks[1]:
            parts = split_row(line)
            if len(parts) < 7:
                continue
            game = parts[0]
            total_rows[game] = {
                "t1_total":   clean_val(parts[1]),
                "t2_total":   clean_val(parts[2]),
                "t3_total":   clean_val(parts[3]),
                "t4_total":   clean_val(parts[4]),
                "t5_total":   clean_val(parts[5]),
                "t6_total":   clean_val(parts[6]),
                "t7_total":   clean_val(parts[7]) if len(parts) > 7 else "",
                "t8_total":   clean_val(parts[8]) if len(parts) > 8 else "",
                "final_total": clean_val(parts[9]) if len(parts) > 9 else "",
                "total_line": clean_val(parts[10]) if len(parts) > 10 else "",
            }

    all_games = sorted(set(list(hcap_rows.keys()) + list(total_rows.keys())))
    rows = []
    for game in all_games:
        home, away = (game.split(" vs ", 1) + [""])[:2]
        row = {
            "season":      2026,
            "round":       round_num,
            "week_ending": week_ending,
            "game":        game,
            "home_team":   home.strip(),
            "away_team":   away.strip(),
        }
        row.update(hcap_rows.get(game, {}))
        row.update(total_rows.get(game, {}))
        rows.append(row)
    return rows


def parse_nrl_ml_shadow(path: Path, round_num: int, week_ending: str) -> list[dict]:
    text = path.read_text(encoding="utf-8")

    margin_rows: dict[str, dict] = {}
    total_rows:  dict[str, dict] = {}
    h2h_rows:    dict[str, dict] = {}

    # Section keywords that start a data block vs. keywords that end one
    SECTION_START = {"MARGIN": "margin", "TOTAL": "total", "H2H": "h2h"}
    SECTION_STOP  = {"FEATURE", "DIVERGENCE", "Legend", "====="}

    current_section = None
    in_data = False  # True once we've seen the horizontal rule after the header

    for line in text.splitlines():
        stripped = line.strip()

        # Detect section starts
        for keyword, name in SECTION_START.items():
            if stripped.startswith(keyword):
                current_section = name
                in_data = False
                break
        else:
            # Detect section stops (reset to None so we don't parse junk)
            for stop in SECTION_STOP:
                if stripped.startswith(stop):
                    current_section = None
                    in_data = False
                    break

        # Horizontal rule signals "data starts now" within the current section
        if re.match(r"^[─\-]{10,}", stripped):
            if current_section:
                in_data = True
            continue

        if not in_data or not current_section:
            continue
        if not stripped or stripped.startswith("="):
            continue

        parts = split_row(line)
        if len(parts) < 4:
            continue
        game = parts[0]
        # Skip column-header rows (they contain words like "Game", "ELO", "ML Raw")
        if any(kw in game for kw in ("Game", "ELO", "ML", "Rules", "Models")):
            continue
        if " vs " not in game:
            continue

        if current_section == "margin":
            # Last 3 cols are always: ML_final, Rules, Diff
            diff     = re.sub(r"[▼▲]$", "", clean_val(parts[-1]))
            rules    = clean_val(parts[-2])
            ml_final = clean_val(parts[-3])
            elo      = clean_val(parts[1])
            ml_raw   = clean_val(parts[2])
            margin_rows[game] = {
                "elo_delta":       elo,
                "ml_raw_margin":   ml_raw,
                "ml_final_margin": ml_final,
                "rules_margin":    rules,
                "margin_diff":     diff,
            }

        elif current_section == "total":
            diff     = re.sub(r"[▼▲]$", "", clean_val(parts[-1]))
            rules    = clean_val(parts[-2])
            ml_final = clean_val(parts[-3])
            ml_raw   = clean_val(parts[1])
            total_rows[game] = {
                "ml_raw_total":    ml_raw,
                "ml_final_total":  ml_final,
                "rules_total":     rules,
                "total_diff":      diff,
            }

        elif current_section == "h2h":
            if len(parts) >= 5:
                h2h_rows[game] = {
                    "ml_raw_h2h_pct":       clean_val(parts[1]).rstrip("%"),
                    "ml_final_h2h_pct":     clean_val(parts[2]).rstrip("%"),
                    "rules_h2h_pct":        clean_val(parts[3]).rstrip("%"),
                    "h2h_diff":             re.sub(r"[▼▲%]", "", clean_val(parts[4])),
                    "ml_home_fair_odds":    clean_val(parts[5]) if len(parts) > 5 else "",
                    "rules_home_fair_odds": clean_val(parts[6]) if len(parts) > 6 else "",
                }

    all_games = sorted(set(
        list(margin_rows.keys()) + list(total_rows.keys()) + list(h2h_rows.keys())
    ))
    rows = []
    for game in all_games:
        home, away = (game.split(" vs ", 1) + [""])[:2]
        row = {
            "season":      2026,
            "round":       round_num,
            "week_ending": week_ending,
            "game":        game,
            "home_team":   home.strip(),
            "away_team":   away.strip(),
        }
        row.update(margin_rows.get(game, {}))
        row.update(total_rows.get(game, {}))
        row.update(h2h_rows.get(game, {}))
        rows.append(row)
    return rows


def parse_afl_pricing(path: Path, round_num: int, week_ending: str) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    blocks = _data_blocks(text)

    # Find the main pricing block: the block whose rows contain ELO numbers and odds
    # Usually the first substantial block
    main_block = None
    for block in blocks:
        # Check if this block has rows with "vs" and numeric values
        data_lines = [l for l in block if " vs " in l and re.search(r"\d+\.\d+", l)]
        if data_lines:
            main_block = data_lines
            break

    if not main_block:
        return []

    # Detect which columns are present from the header line that preceded the block
    # Infer from the number of values per row
    rows = []
    for line in main_block:
        # Strip flag chars
        line_clean = re.sub(r"\s*[⚑◆⚡]+", "", line)
        parts = split_row(line_clean)
        if len(parts) < 5 or " vs " not in parts[0]:
            continue

        home, away = (parts[0].split(" vs ", 1) + [""])[:2]
        n = len(parts)

        # Last two columns are always home_odds, away_odds
        # Second to last group: FinalMrg, FinalTot, HomeOdds, AwayOdds
        home_odds = clean_val(parts[-1])
        away_odds = clean_val(parts[-2])  # No — odds come as HomeOdds AwayOdds at end
        # Actually: ... FinalMrg  FinalTot   HomeOdds  AwayOdds
        # So parts[-4] = FinalMrg, parts[-3] = FinalTot, parts[-2] = HomeOdds, parts[-1] = AwayOdds
        final_mrg  = clean_val(parts[-4]) if n >= 4 else ""
        final_tot  = clean_val(parts[-3]) if n >= 3 else ""
        home_odds  = clean_val(parts[-2]) if n >= 2 else ""
        away_odds  = clean_val(parts[-1]) if n >= 1 else ""

        # Tier columns sit between the game name (parts[0]) and final values
        # parts[1] = ELO (integer like +49 or -153)
        # parts[2] = T1 Mrg
        # parts[3..n-5] = tier adjustments (T2, T3, T4, T5, T6, T7)
        tier_vals = parts[3 : n - 4] if n > 7 else []
        tier_names = ["t2_hcap", "t3_hcap", "t4_hcap", "t5_hcap", "t6_hcap", "t7_hcap"]

        row = {
            "season":      2026,
            "round":       round_num,
            "week_ending": week_ending,
            "game":        parts[0],
            "home_team":   home.strip(),
            "away_team":   away.strip(),
            "elo":         clean_val(parts[1]) if n > 1 else "",
            "t1_margin":   clean_val(parts[2]) if n > 2 else "",
        }
        for i, tname in enumerate(tier_names):
            row[tname] = clean_val(tier_vals[i]) if i < len(tier_vals) else ""

        row["final_margin"] = final_mrg
        row["final_total"]  = final_tot
        row["home_odds"]    = home_odds
        row["away_odds"]    = away_odds
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUT_NRL.mkdir(parents=True, exist_ok=True)
    OUT_AFL.mkdir(parents=True, exist_ok=True)

    # --- NRL: copy existing pricing CSVs ---
    nrl_copies = [
        (ROOT / "results" / "r9_pricing_2026.csv",  "NRL_PRICING_R09_2026-04-28.csv"),
        (ROOT / "results" / "r10_pricing_2026.csv", "NRL_PRICING_R10_2026-05-05.csv"),
        (ROOT / "results" / "r11_pricing_2026.csv", "NRL_PRICING_R11_2026-05-12.csv"),
        (ROOT / "results" / "r12_pricing_2026.csv", "NRL_PRICING_R12_2026-05-25.csv"),
        (ROOT / "results" / "r14_pricing_2026.csv", "NRL_PRICING_R14_2026-06-04.csv"),
    ]
    print("\nNRL — copying pricing CSVs:")
    for src, name in nrl_copies:
        if src.exists():
            copy_csv(src, OUT_NRL / name)
        else:
            print(f"  MISSING: {src.name}")

    # --- NRL: tier breakdown txt → CSV ---
    print("\nNRL — converting tier breakdown:")
    tb_src = ROOT / "results" / "r9_2026_tier_breakdown.txt"
    if tb_src.exists():
        rows = parse_nrl_tier_breakdown(tb_src, 9, "2026-04-28")
        write_csv(rows, OUT_NRL / "NRL_PRICING_R09_2026-04-28_tier_breakdown.csv")

    # --- NRL: ml_shadow txt → CSV ---
    print("\nNRL — converting ML shadow files:")
    ml_shadow_sources = [
        (ROOT / "data/clv/nrl/NRL_CLV_R09_2026-04-28_ml_shadow.txt", 9,  "2026-04-28"),
        (ROOT / "data/clv/nrl/NRL_CLV_R10_2026-05-05_ml_shadow.txt", 10, "2026-05-05"),
        (ROOT / "data/clv/nrl/NRL_CLV_R11_2026-05-19_ml_shadow.txt", 11, "2026-05-12"),
    ]
    for src, rnd, week in ml_shadow_sources:
        if src.exists():
            rows = parse_nrl_ml_shadow(src, rnd, week)
            name = f"NRL_PRICING_R{rnd:02d}_{week}_ml_shadow.csv"
            write_csv(rows, OUT_NRL / name)
        else:
            print(f"  MISSING: {src.name}")

    # --- AFL: convert txt pricing files ---
    print("\nAFL — converting pricing txt files:")
    afl_txt_sources = [
        (ROOT / "results" / "r7_afl_2026.txt",          7,  "2026-04-28", ""),
        (ROOT / "results" / "r7_afl_2026_t1t2t3t4.txt", 7,  "2026-04-28", "_t1t2t3t4"),
        (ROOT / "results" / "r8_afl_2026.txt",          8,  "2026-05-05", ""),
    ]
    for src, rnd, week, suffix in afl_txt_sources:
        if src.exists():
            rows = parse_afl_pricing(src, rnd, week)
            name = f"AFL_PRICING_R{rnd:02d}_{week}{suffix}.csv"
            write_csv(rows, OUT_AFL / name)
        else:
            print(f"  MISSING: {src.name}")

    # --- AFL: copy existing pricing CSVs ---
    print("\nAFL — copying pricing CSVs:")
    afl_r9_src = ROOT / "outputs" / "afl_round_prep" / "r9_2026" / "afl_r9_pricing_2026.csv"
    afl_copies = [
        (afl_r9_src,                                   "AFL_PRICING_R09_2026-05-12.csv"),
        (ROOT / "results" / "r11_afl_2026.csv",        "AFL_PRICING_R11_2026-05-25.csv"),
    ]
    for src, name in afl_copies:
        if src.exists():
            copy_csv(src, OUT_AFL / name)
        else:
            print(f"  MISSING: {src.name}")

    # --- Summary ---
    nrl_files = sorted(OUT_NRL.glob("*.csv"))
    afl_files = sorted(OUT_AFL.glob("*.csv"))
    print(f"\nDone.")
    print(f"\n  data/pricing/nrl/  ({len(nrl_files)} files)")
    for f in nrl_files:
        print(f"    {f.name}")
    print(f"\n  data/pricing/afl/  ({len(afl_files)} files)")
    for f in afl_files:
        print(f"    {f.name}")


if __name__ == "__main__":
    main()
