"""
Push NRL match history to Supabase betmate_data_store key 'nrl_match_history'.
Reads from data/nrl/historical/latest.xlsx (2024+ only).
Run after each weekly download of the Excel file.
"""
import os, json, sys
from datetime import datetime
from pathlib import Path
import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
EXCEL = ROOT / "data/nrl/historical/latest.xlsx"
ENV = ROOT / ".env.local"

def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def normalize(name: str) -> str:
    return name.lower().replace(".", "").replace("-", " ").strip()

def extract_matches(cutoff_year=2024):
    wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.rows)
    matches = []
    for row in rows[2:]:  # skip header rows
        vals = [cell.value for cell in row[:10]]
        date, _, home, away, venue, hs, aws = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6]
        if not isinstance(date, datetime) or date.year < cutoff_year:
            continue
        if not isinstance(hs, int) or not isinstance(aws, int):
            continue
        matches.append({
            "date": date.strftime("%Y-%m-%d"),
            "homeTeam": home or "",
            "awayTeam": away or "",
            "homeScore": hs,
            "awayScore": aws,
            "venue": venue or "",
        })
    wb.close()
    # Newest first (Excel is already newest-first from row 2)
    return matches

def push(env, matches):
    url = env["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = {"key": "nrl_match_history", "data": matches}
    # Upsert
    r = requests.post(f"{url}/rest/v1/betmate_data_store", headers=headers, json=payload)
    if r.status_code in (200, 201):
        print(f"Pushed {len(matches)} NRL matches to Supabase.")
    else:
        print(f"Error {r.status_code}: {r.text}")

if __name__ == "__main__":
    env = load_env()
    matches = extract_matches(cutoff_year=2024)
    print(f"Extracted {len(matches)} NRL matches (2024+)")
    if matches:
        print(f"  Newest: {matches[0]['date']} {matches[0]['homeTeam']} vs {matches[0]['awayTeam']}")
        print(f"  Oldest: {matches[-1]['date']} {matches[-1]['homeTeam']} vs {matches[-1]['awayTeam']}")
    push(env, matches)
