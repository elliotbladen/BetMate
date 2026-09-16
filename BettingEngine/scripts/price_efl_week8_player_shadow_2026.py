"""Week 8 Championship normal plus player-shadow comparison run."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scripts import price_efl_week7_normal_shadow_2026 as base
base.FIXTURES=[('2026-09-18','Bristol City','Watford'),('2026-09-19','Cardiff','Charlton'),('2026-09-19','Millwall','West Ham'),('2026-09-19','Stoke','Sheffield United'),('2026-09-19','Birmingham','Middlesbrough'),('2026-09-19','Portsmouth','Blackburn'),('2026-09-19','Burnley','Derby'),('2026-09-19','Lincoln','Swansea'),('2026-09-19','QPR','Preston'),('2026-09-19','Wrexham','Southampton'),('2026-09-20','Wolves','West Brom'),('2026-09-20','Norwich','Bolton')]
base.GAMES_PLAYED={'Birmingham':7,'Blackburn':7,'Bolton':7,'Burnley':7,'Cardiff':7,'Charlton':7,'Derby':7,'Norwich':7,'Preston':7,'QPR':7,'Sheffield United':7,'Southampton':7,'Stoke':7,'Swansea':7,'Watford':7,'West Brom':7,'West Ham':7,'Wrexham':7,'Bristol City':6,'Lincoln':6,'Middlesbrough':6,'Millwall':6,'Portsmouth':6,'Wolves':6}
base.ABSENCES={}; base.DOUBTS={}; base.NEW_MANAGERS=set()
base.MARKET={f'{h} v {a}':{'avg_home':2.0,'avg_draw':3.5,'avg_away':3.5,'avg_over25':2.0,'avg_under25':2.0} for _,h,a in base.FIXTURES}
base.OUTDIR=ROOT/'outputs/football/championship/2026-27/gw08_player_shadow'; base.SUPPORT=base.OUTDIR/'_supporting'
_original=base.price_match
def _price(*args,**kwargs):
    for key in ('mkt_home','mkt_draw','mkt_away','mkt_over25'):
        kwargs.pop(key, None)
    return _original(*args,**kwargs)
base.price_match=_price
if __name__=='__main__': base.main()
