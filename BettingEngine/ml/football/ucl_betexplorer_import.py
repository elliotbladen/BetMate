import re
from pathlib import Path
import pandas as pd

OUT = Path("BettingEngine/data/ucl/markets/ucl_betexplorer_2024_25_1x2.csv")
rows = []
import urllib.request, ssl
sources = [Path("tmp_betexp_results_2425.html").read_text(encoding="utf-8"), Path("tmp_betexp_league2425.html").read_text(encoding="utf-8")]
for source in sources:
    for tr in re.findall(r"<tr>(.*?)</tr>", source, re.S):
        if "data-test=" not in tr:
            continue
        anchor = re.search(r'<a[^>]+class="in-match"[^>]*>(.*?)</a>', tr, re.S)
        span_names = re.findall(r'<span[^>]*>(?:<strong>)?([^<]+)', anchor.group(1), re.S) if anchor else []
        odds = re.findall(r'data-odd="([0-9.]+)"', tr)
        date = re.search(r"(\d{2}\.\d{2}\.(?:2024|2025))", tr)
        score = re.search(r"(\d+:\d+)", tr)
        if len(span_names) >= 2 and len(odds) >= 3 and date and score:
            rows.append([date.group(1), span_names[0].strip(), span_names[1].strip(), score.group(1), *odds[:3]])
OUT.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows, columns=["date", "home_slug", "away_slug", "score", "home_odds", "draw_odds", "away_odds"]).to_csv(OUT, index=False)
print({"rows": len(rows), "output": str(OUT)})
