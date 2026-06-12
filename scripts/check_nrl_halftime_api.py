"""Debug NRL API response."""
import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.nrl.com/draw/",
    "Origin": "https://www.nrl.com",
}

for season, rnd in [(2026, 15), (2025, 14), (2023, 14)]:
    url = f"https://www.nrl.com/draw/data/?competition=111&season={season}&round={rnd}"
    r = requests.get(url, headers=headers, timeout=15)
    print(f"{season} R{rnd}: status={r.status_code} len={len(r.text)} content_type={r.headers.get('content-type','')}")
    if r.status_code == 200 and r.text.strip():
        try:
            d = r.json()
            fixtures = [f for f in d.get("fixtures", []) if f.get("type") == "Match"]
            print(f"  -> {len(fixtures)} fixtures found")
            if fixtures:
                f = fixtures[0]
                home = f.get("homeTeam", {}).get("nickName", "?")
                away = f.get("awayTeam", {}).get("nickName", "?")
                date = f.get("clock", {}).get("kickOffTimeLong", "")[:10]
                print(f"  -> First: {home} vs {away} on {date}")
        except Exception as e:
            print(f"  -> JSON parse error: {e}, body: {r.text[:200]}")
    else:
        print(f"  -> Body: {r.text[:200]}")
