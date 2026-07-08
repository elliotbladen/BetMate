"""Probe RLP page structure before writing the full scraper."""
import requests
from bs4 import BeautifulSoup

url = "https://www.rugbyleagueproject.org/referees/todd-smith-ref/games.html"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

print("Fetching page...")
resp = requests.get(url, headers=headers, timeout=30)
print(f"Status: {resp.status_code}  |  Size: {len(resp.text):,} bytes")

soup = BeautifulSoup(resp.text, "html.parser")

# Find all tables and print their headers
tables = soup.find_all("table")
print(f"\nFound {len(tables)} tables")
for i, t in enumerate(tables):
    ths = [th.get_text(strip=True) for th in t.find_all("th")]
    rows = t.find_all("tr")
    print(f"\nTable {i}: {len(rows)} rows | Headers: {ths[:15]}")

# Show first table with 'Score' in headers
print("\n--- SAMPLE ROWS from games table ---")
for t in tables:
    ths = [th.get_text(strip=True) for th in t.find_all("th")]
    if "Score" in ths or "score" in [h.lower() for h in ths]:
        print(f"Headers: {ths}")
        rows = t.find_all("tr")
        # Show last 15 rows (most recent games)
        print(f"\nLast 15 data rows (most recent):")
        data_rows = [r for r in rows if r.find("td")]
        for row in data_rows[-15:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            print(cells)
        break
