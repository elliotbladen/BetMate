"""Week 5 EPL normal plus player-shadow comparison run."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scripts import price_epl_week3_normal_shadow_2026 as base
base.FIXTURES=[
 ('2026-09-18','Brentford','Chelsea'),('2026-09-19','Tottenham','Aston Villa'),('2026-09-19','Brighton','Arsenal'),('2026-09-19','Everton','Ipswich'),('2026-09-19','Newcastle','Hull'),('2026-09-19',"Nott'm Forest",'Coventry'),('2026-09-20','Bournemouth','Liverpool'),('2026-09-20','Leeds','Crystal Palace'),('2026-09-20','Man City','Sunderland'),('2026-09-20','Fulham','Man United')]
base.ABSENCES={
 'Liverpool':[('Hugo Ekitike','ST'),('Conor Bradley','RB'),('Giovanni Leoni','CB'),('Federico Chiesa','FW')],
 'Tottenham':[('Mykhailo Mudryk','LW'),('Xavi Simons','AM'),('Wilson Odobert','LW'),('Dejan Kulusevski','AM'),('Pedro Porro','RB'),('Sandro Tonali','CM')],
 'Brentford':[('Kaye Furo','CM'),('Nathan Collins','CB'),('Mathias Jensen','CM'),('Sepp van den Berg','CB'),('Josh Dasilva','CM'),('Antoni Milambo','CM')],
 'Fulham':[('Tom Cairney','CM'),('Ryan Sessegnon','LB')], 'Ipswich':[('Jack Taylor','CM')], 'Man City':[('Jeremy Doku','LW')], 'Aston Villa':[('Joao Gomes','CM')]}
base.DOUBTS={'Ipswich':["Emersonn (ST, won't be risked midweek)"], 'Liverpool':['Joe Gomez (muscle) — back in training, available']}
base.OUT_JSON=ROOT/'outputs/football/epl/2026-27/gw05_player_shadow_prices.json'
base.OUT_MD=ROOT/'outputs/football/epl/2026-27/gw05_player_shadow_prices.md'
base.OUT_WORKING=ROOT/'outputs/football/epl/2026-27/gw05_player_shadow_full_working.txt'
_original=base.price_match
def _price(*args,**kwargs): kwargs['matchweek']=5; return _original(*args,**kwargs)
base.price_match=_price
if __name__=='__main__': base.main()
