"""Repair 2025/26 UCL fixture dates using Footiqo's public match calendar."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/ucl/matches/ucl_matches_openfootball.csv"
ODDS = ROOT / "data/ucl/markets/ucl_footiqo_closing_1x2_2025_26.csv"
OUT = ROOT / "data/ucl/matches/ucl_matches_openfootball_repaired.csv"
MAP_OUT = ROOT / "data/ucl/markets/ucl_footiqo_match_mapping_2025_26.csv"

ALIASES = {
    "Athletic Club (ESP)": "Ath Bilbao", "AFC Ajax (NED)": "Ajax",
    "AS Monaco FC (MCO)": "Monaco", "Borussia Dortmund (GER)": "Dortmund",
    "FC Barcelona (ESP)": "Barcelona", "FC Bayern München (GER)": "Bayern Munich",
    "FC Internazionale Milano (ITA)": "Inter", "FC København (DEN)": "FC Copenhagen",
    "FK Bodø/Glimt (NOR)": "Bodo/Glimt", "FK Kairat (KAZ)": "Kairat Almaty",
    "Newcastle United FC (ENG)": "Newcastle", "Olympique de Marseille (FRA)": "Marseille",
    "PAE Olympiakos SFP (GRE)": "Olympiacos Piraeus", "Paphos FC (CYP)": "Pafos",
    "Paris Saint-Germain FC (FRA)": "PSG", "Qarabağ Ağdam FK (AZE)": "Qarabag",
    "Real Madrid CF (ESP)": "Real Madrid", "SK Slavia Praha (CZE)": "Slavia Prague",
    "SSC Napoli (ITA)": "Napoli", "Sport Lisboa e Benfica (POR)": "Benfica",
    "Sporting Clube de Portugal (POR)": "Sporting CP", "Tottenham Hotspur FC (ENG)": "Tottenham",
    "Villarreal CF (ESP)": "Villarreal", "Royale Union Saint-Gilloise (BEL)": "Royale Union SG",
}

def repair() -> dict:
    matches = pd.read_csv(SOURCE)
    odds = pd.read_csv(ODDS)
    cur = matches[matches.season.eq("2025-26")].copy()
    def map_name(value):
        # OpenFootball's legacy CSV contains occasional mojibake; use stable
        # distinctive fragments so those rows still resolve safely.
        text = str(value)
        if text in ALIASES:
            return ALIASES[text]
        low = text.lower()
        fragments = {
            "athletic club": "Ath Bilbao", "ajax": "Ajax", "monaco": "Monaco",
            "arsenal": "Arsenal", "psv": "PSV", "juventus": "Juventus", "atalanta": "Atalanta",
            "leverkusen": "Bayer Leverkusen", "club brugge": "Club Brugge KV", "chelsea": "Chelsea",
            "liverpool": "Liverpool", "manchester city": "Manchester City", "eintracht": "Eintracht Frankfurt",
            "galatasaray": "Galatasaray", "bayern": "Bayern Munich",
            "dortmund": "Dortmund", "barcelona": "Barcelona", "bayern": "Bayern Munich",
            "internazionale": "Inter", "københavn": "FC Copenhagen", "kbenhavn": "FC Copenhagen",
            "bod": "Bodo/Glimt", "kairat": "Kairat Almaty", "newcastle": "Newcastle",
            "marseille": "Marseille", "olympiak": "Olympiacos Piraeus", "paphos": "Pafos",
            "paris saint": "PSG", "qarab": "Qarabag", "real madrid": "Real Madrid",
            "slavia": "Slavia Prague", "napoli": "Napoli", "benfica": "Benfica",
            "sporting": "Sporting CP", "tottenham": "Tottenham", "villarreal": "Villarreal",
            "atletico": "Atl. Madrid", "atl�tico": "Atl. Madrid", "club atl": "Atl. Madrid", "union": "Royale Union SG",
        }
        for fragment, replacement in fragments.items():
            if fragment in low:
                return replacement
        return text
    cur["odds_home"] = cur.home_name_source.map(map_name)
    cur["odds_away"] = cur.away_name_source.map(map_name)
    cur["pair_n"] = cur.groupby(["odds_home", "odds_away"]).cumcount()
    odds["pair_n"] = odds.groupby(["homeTeam", "awayTeam"]).cumcount()
    lookup = odds[["homeTeam", "awayTeam", "pair_n", "matchDate", "xbetClose1FT", "xbetCloseXFT", "xbetClose2FT", "xbetCloseOver25", "xbetCloseUnder25"]].rename(columns={"homeTeam":"odds_home", "awayTeam":"odds_away"})
    repaired = cur.merge(lookup, on=["odds_home", "odds_away", "pair_n"], how="left")
    repaired["kickoff_utc"] = pd.to_datetime(repaired.matchDate, dayfirst=True, errors="coerce", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    matches = matches.set_index("match_id")
    repaired = repaired.set_index("match_id")
    matches.loc[repaired.index, "kickoff_utc"] = repaired["kickoff_utc"]
    matches.reset_index().to_csv(OUT, index=False)
    mapping = repaired.reset_index()[["match_id", "matchDate", "odds_home", "odds_away", "xbetClose1FT", "xbetCloseXFT", "xbetClose2FT", "xbetCloseOver25", "xbetCloseUnder25"]].rename(columns={"odds_home":"homeTeam", "odds_away":"awayTeam"})
    mapping.to_csv(MAP_OUT, index=False)
    return {"season":"2025-26", "rows":len(cur), "dates_repaired":int(repaired.kickoff_utc.notna().sum()), "output":str(OUT), "mapping":str(MAP_OUT)}

if __name__ == "__main__":
    print(repair())
