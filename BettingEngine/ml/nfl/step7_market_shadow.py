"""NFL Step 7: append-only market capture and tier-shadow comparisons.

The collector can fetch The Odds API or ingest an exported response. A failed or
expired subscription never creates a market snapshot. Predictions remain frozen;
all output is written beside them as new, timestamped evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "data/nfl/predictions/2026_week01_paper_frozen.csv"
PREDICTION_MANIFEST = ROOT / "ml/nfl/reports/step6_week01_prediction_manifest.json"
ARCHIVE_ROOT = ROOT / "data/nfl/markets/step7"
REPORT_ROOT = ROOT / "ml/nfl/reports/step7"
SPORT_KEY = "americanfootball_nfl"
API_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds/"

TEAM_CODES = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}

FIELDS = [
    "capture_id", "game_id", "event_id", "captured_at_utc", "quote_updated_at_utc",
    "kickoff_at_utc", "bookmaker", "home_team", "away_team", "home_spread", "total",
    "home_spread_price", "away_spread_price", "over_price", "under_price",
    "home_h2h_price", "away_h2h_price", "valid_obtainable_quote", "qualification_reason",
]


def _aware_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _api_key() -> str:
    if os.environ.get("ODDS_API_KEY"):
        return os.environ["ODDS_API_KEY"]
    env_path = ROOT.parent / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ODDS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def fetch_payload(api_key: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not api_key:
        raise RuntimeError("ODDS_API_KEY is missing or expired")
    query = urllib.parse.urlencode({
        "apiKey": api_key, "regions": "au,uk,us", "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal", "dateFormat": "iso",
    })
    request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": "BetMate-NFL-Step7/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            headers = {
                "requests_remaining": response.headers.get("x-requests-remaining", ""),
                "requests_used": response.headers.get("x-requests-used", ""),
            }
            return json.loads(response.read().decode("utf-8")), headers
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 402, 403, 429}:
            raise RuntimeError(f"Odds API unavailable (HTTP {exc.code}); subscription/key may be inactive") from exc
        raise RuntimeError(f"Odds API request failed (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Odds API network failure: {exc.reason}") from exc


def _market(markets: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    return next((item for item in markets if item.get("key") == key), None)


def _outcome(market: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not market:
        return None
    return next((item for item in market.get("outcomes", []) if item.get("name") == name), None)


def _price(item: dict[str, Any] | None) -> float | None:
    return float(item["price"]) if item and item.get("price") is not None else None


def _point(item: dict[str, Any] | None) -> float | None:
    return float(item["point"]) if item and item.get("point") is not None else None


def normalize_payload(payload: list[dict[str, Any]], captured_at: datetime) -> list[dict[str, Any]]:
    """Flatten Odds API events to one validated row per game and bookmaker."""
    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    rows: list[dict[str, Any]] = []
    capture_id = _stamp(captured_at)
    for event in payload:
        home_name, away_name = event.get("home_team", ""), event.get("away_team", "")
        home_code, away_code = TEAM_CODES.get(home_name), TEAM_CODES.get(away_name)
        game_id = ""
        reasons: list[str] = []
        try:
            kickoff = _aware_utc(event.get("commence_time", ""))
        except (TypeError, ValueError):
            kickoff = None
            reasons.append("invalid_kickoff_timestamp")
        if home_code and away_code and kickoff:
            # The schedule ID is resolved from the frozen card below; this candidate
            # is retained only for transparent diagnostics.
            candidates = pd.read_csv(PREDICTIONS) if PREDICTIONS.exists() else pd.DataFrame()
            match = candidates[(candidates.home_team == home_code) & (candidates.away_team == away_code)]
            if len(match) == 1:
                game_id = str(match.iloc[0].game_id)
            else:
                reasons.append("unmapped_or_ambiguous_matchup")
        else:
            reasons.append("unknown_team_mapping")
        for book in event.get("bookmakers", []):
            markets = book.get("markets", [])
            spread, total, h2h = _market(markets, "spreads"), _market(markets, "totals"), _market(markets, "h2h")
            home_spread, away_spread = _outcome(spread, home_name), _outcome(spread, away_name)
            over, under = _outcome(total, "Over"), _outcome(total, "Under")
            home_h2h, away_h2h = _outcome(h2h, home_name), _outcome(h2h, away_name)
            book_reasons = list(reasons)
            try:
                updated = _aware_utc(book.get("last_update", ""))
            except (TypeError, ValueError):
                updated = None
                book_reasons.append("invalid_quote_timestamp")
            if not book.get("key"):
                book_reasons.append("missing_bookmaker")
            hs, aws, line_total = _point(home_spread), _point(away_spread), _point(over)
            if hs is None and line_total is None and _price(home_h2h) is None:
                book_reasons.append("no_supported_market")
            if hs is not None and aws is not None and abs(hs + aws) > 1e-9:
                book_reasons.append("spread_sign_mismatch")
            if over and under and _point(under) != line_total:
                book_reasons.append("total_line_mismatch")
            prices = [_price(x) for x in (home_spread, away_spread, over, under, home_h2h, away_h2h)]
            if any(price is not None and price <= 1.0 for price in prices):
                book_reasons.append("invalid_decimal_price")
            if kickoff and updated and updated >= kickoff:
                book_reasons.append("quote_not_before_kickoff")
            rows.append({
                "capture_id": capture_id, "game_id": game_id, "event_id": event.get("id", ""),
                "captured_at_utc": captured_at.astimezone(timezone.utc).isoformat(),
                "quote_updated_at_utc": updated.isoformat() if updated else "",
                "kickoff_at_utc": kickoff.isoformat() if kickoff else "", "bookmaker": book.get("key", ""),
                "home_team": home_code or home_name, "away_team": away_code or away_name,
                "home_spread": hs, "total": line_total,
                "home_spread_price": _price(home_spread), "away_spread_price": _price(away_spread),
                "over_price": _price(over), "under_price": _price(under),
                "home_h2h_price": _price(home_h2h), "away_h2h_price": _price(away_h2h),
                "valid_obtainable_quote": not book_reasons,
                "qualification_reason": "valid" if not book_reasons else "|".join(dict.fromkeys(book_reasons)),
            })
    return rows


def _write_csv_once(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite archived capture: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_shadow(rows: list[dict[str, Any]], captured_at: datetime) -> list[dict[str, Any]]:
    predictions = pd.read_csv(PREDICTIONS)
    valid = pd.DataFrame([row for row in rows if row["valid_obtainable_quote"]])
    output: list[dict[str, Any]] = []
    for prediction in predictions.to_dict("records"):
        quotes = valid[valid.game_id == prediction["game_id"]] if not valid.empty else pd.DataFrame()
        spread_values = quotes.home_spread.dropna().tolist() if not quotes.empty else []
        total_values = quotes.total.dropna().tolist() if not quotes.empty else []
        market_spread = float(median(spread_values)) if spread_values else None
        market_total = float(median(total_values)) if total_values else None
        spread_edge = (market_spread - float(prediction["ridge_fair_home_spread"])) if market_spread is not None else None
        total_edge = (float(prediction["ridge_total"]) - market_total) if market_total is not None else None
        tree_spread_edge = (market_spread - float(prediction["tree_shadow_fair_home_spread"])) if market_spread is not None else None
        spread_dispersion = max(spread_values) - min(spread_values) if spread_values else None
        total_dispersion = max(total_values) - min(total_values) if total_values else None
        t8 = classify_market_disagreement(spread_edge, tree_spread_edge, total_edge,
                                         spread_dispersion, total_dispersion)
        output.append({
            "capture_id": _stamp(captured_at), "game_id": prediction["game_id"],
            "home_team": prediction["home_team"], "away_team": prediction["away_team"],
            "fair_home_spread": prediction["ridge_fair_home_spread"], "consensus_home_spread": market_spread,
            "spread_edge_home_points": spread_edge, "fair_total": prediction["ridge_total"],
            "consensus_total": market_total, "total_edge_over_points": total_edge,
            "spread_book_dispersion": spread_dispersion, "total_book_dispersion": total_dispersion,
            "t8_spread_status": t8["spread_status"], "t8_total_status": t8["total_status"],
            "t8_spread_model_agreement": t8["spread_model_agreement"],
            "valid_bookmakers": int(quotes.bookmaker.nunique()) if not quotes.empty else 0,
            "t0_data_gate": "pass" if not quotes.empty else "fail_no_valid_quote",
            "t1_structural": "active_paper", "t2_qb_personnel": "shadow_unresolved",
            "t3_continuity_injuries": "shadow_unresolved", "decision": "WATCH" if not quotes.empty else "PASS",
            "staking_enabled": False, "reason": "selection_threshold_not_authorised" if not quotes.empty else "no_valid_quote",
        })
    return output


def classify_market_disagreement(spread_edge: float | None, tree_spread_edge: float | None,
                                total_edge: float | None, spread_dispersion: float | None,
                                total_dispersion: float | None) -> dict[str, Any]:
    """Research-only T8 state; no selection or stake is authorised."""
    def status(edge: float | None, dispersion: float | None) -> str:
        if edge is None:
            return "unresolved"
        if dispersion is not None and dispersion > 2.0:
            return "watch_unstable_market"
        magnitude = abs(edge)
        return "watch_large" if magnitude >= 3.0 else "watch_medium" if magnitude >= 2.0 else "watch_small"

    agreement = None if spread_edge is None or tree_spread_edge is None else (
        spread_edge == 0 or tree_spread_edge == 0 or (spread_edge > 0) == (tree_spread_edge > 0)
    )
    return {"spread_status": status(spread_edge, spread_dispersion),
            "total_status": status(total_edge, total_dispersion),
            "spread_model_agreement": agreement, "betting_action": "none"}


def capture(payload: list[dict[str, Any]], captured_at: datetime, source: str, api_meta: dict[str, str] | None = None) -> dict[str, Any]:
    if not PREDICTIONS.exists() or not PREDICTION_MANIFEST.exists():
        raise RuntimeError("Step 6 frozen predictions are required")
    prediction_manifest = json.loads(PREDICTION_MANIFEST.read_text(encoding="utf-8"))
    if _sha256(PREDICTIONS) != prediction_manifest["sha256"]["prediction"]:
        raise RuntimeError("Step 6 prediction hash mismatch")
    rows = normalize_payload(payload, captured_at)
    if not rows:
        return {"status": "no_market_events", "archived": False, "quotes": 0, "valid_quotes": 0}
    stamp = _stamp(captured_at)
    archive = ARCHIVE_ROOT / str(captured_at.year) / "week01" / f"{stamp}.csv"
    shadow_path = REPORT_ROOT / f"week01_shadow_{stamp}.csv"
    manifest_path = REPORT_ROOT / f"week01_capture_{stamp}.json"
    _write_csv_once(archive, rows)
    shadow = build_shadow(rows, captured_at)
    shadow_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(shadow).to_csv(shadow_path, index=False)
    manifest = {
        "status": "captured", "source": source, "captured_at_utc": captured_at.astimezone(timezone.utc).isoformat(),
        "quotes": len(rows), "valid_quotes": sum(bool(row["valid_obtainable_quote"]) for row in rows),
        "games_with_valid_quotes": len({row["game_id"] for row in rows if row["valid_obtainable_quote"]}),
        "staking_enabled": False, "prediction_sha256": _sha256(PREDICTIONS),
        "archive": str(archive.relative_to(ROOT)), "archive_sha256": _sha256(archive),
        "shadow": str(shadow_path.relative_to(ROOT)), "shadow_sha256": _sha256(shadow_path),
        "api_meta": api_meta or {},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL Step 7 market shadow collector")
    parser.add_argument("action", choices=("collect", "import-file", "validate-file"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--captured-at", help="Timezone-aware ISO timestamp; defaults to now")
    args = parser.parse_args()
    captured_at = _aware_utc(args.captured_at) if args.captured_at else datetime.now(timezone.utc)
    try:
        if args.action == "collect":
            payload, meta = fetch_payload(_api_key())
            result = capture(payload, captured_at, "the_odds_api", meta)
        else:
            if not args.input:
                parser.error("--input is required")
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            rows = normalize_payload(payload, captured_at)
            if args.action == "validate-file":
                result = {"status": "validated", "archived": False, "quotes": len(rows),
                          "valid_quotes": sum(bool(row["valid_obtainable_quote"]) for row in rows)}
            else:
                result = capture(payload, captured_at, f"offline_file:{args.input.name}")
    except RuntimeError as exc:
        result = {"status": "upstream_unavailable", "archived": False, "staking_enabled": False, "reason": str(exc)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
