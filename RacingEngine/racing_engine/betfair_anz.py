"""Read official Betfair Australia/NZ thoroughbred closing-price files."""
from __future__ import annotations

import csv,io,zipfile
from pathlib import Path
from typing import Iterator

from .horse_identity import identity_key

TRACK_ALIASES={
    "randwick":"randwick","royal randwick":"randwick","rosehill":"rosehill",
    "rosehill gardens":"rosehill","flemington":"flemington","caulfield":"caulfield",
    "caulfield heath":"caulfield-heath","moonee valley":"the-valley","the valley":"the-valley",
    "sandown":"sportsbet-sandown-hillside","sandown hillside":"sportsbet-sandown-hillside",
    "sportsbet sandown hillside":"sportsbet-sandown-hillside",
    "sandown lakeside":"sportsbet-sandown-lakeside","sportsbet sandown lakeside":"sportsbet-sandown-lakeside",
}


def track_slug(value:str)->str|None:
    return TRACK_ALIASES.get((value or "").strip().lower())


def _readers(root:Path)->Iterator[csv.DictReader]:
    archive=root/"ANZ_Thoroughbreds_2025.zip"
    with zipfile.ZipFile(archive) as bundle:
        for name in sorted(bundle.namelist()):
            if name.endswith(("_08.csv","_09.csv","_10.csv","_11.csv","_12.csv")):
                with bundle.open(name) as raw:
                    yield csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8-sig",newline=""))
    for path in sorted(root.glob("ANZ_Thoroughbreds_2026_*.csv")):
        with path.open(encoding="utf-8-sig",newline="") as handle:
            yield csv.DictReader(handle)


def relevant_rows(root:Path,start_date:str,end_date:str)->Iterator[dict]:
    for reader in _readers(root):
        for row in reader:
            day=row["LOCAL_MEETING_DATE"]
            slug=track_slug(row["TRACK"])
            if start_date<=day<=end_date and slug and row.get("STATE_CODE") in ("NSW","VIC"):
                close=row.get("BEST_AVAIL_BACK_AT_SCHEDULED_OFF")
                bsp=row.get("WIN_BSP")
                try:close_price=float(close) if close else None
                except ValueError:close_price=None
                try:bsp_price=float(bsp) if bsp else None
                except ValueError:bsp_price=None
                yield {"race_date":day,"track_slug":slug,"state":row["STATE_CODE"],
                    "race_number":int(row["RACE_NO"]),"runner_number":int(float(row["TAB_NUMBER"])),
                    "horse_key":identity_key(row["SELECTION_NAME"]),"horse_name":row["SELECTION_NAME"],
                    "close_price":close_price,"bsp":bsp_price,"result":row["WIN_RESULT"],
                    "market_id":row["WIN_MARKET_ID"],"scheduled_time":row["SCHEDULED_RACE_TIME"],
                    "back_market_percentage":row.get("BACK_MARKET_PERCENTAGE_AT_SCHEDULED_OFF")}
