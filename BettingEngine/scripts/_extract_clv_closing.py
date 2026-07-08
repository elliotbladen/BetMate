import csv, sys

path = sys.argv[1]
rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
for r in rows:
    home = r['home_team'].split()[-1]
    away = r['away_team'].split()[-1]
    sig  = r.get('signal','')
    if sig in ('model','market','normal','ml'):
        line = (
            f"{home} v {away}"
            f" | {r['market']:10}"
            f" | sig={sig:6}"
            f" | sel={r['selection'][:22]:22}"
            f" | open_num={r['open_number']:7}"
            f" close_num={r['close_number']:7}"
            f" | open_odds={r['open_odds']:6}"
            f" close_odds={r['close_odds']:6}"
            f" | clv={r['clv']:8}"
        )
        print(line)
