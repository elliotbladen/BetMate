import sqlite3
import pytest
from racing_engine.trial_official_archive import parse,source_url,install,SCHEMA
from racing_engine.trial_meeting import MeetingError
ITEM={'date':'2026-08-18','state':'QLD','venue':'Test Park','isTrial':True,'isJumpOut':False}
NOW='2026-09-14T00:00:00+00:00'

def page():
    key='2026Aug18,QLD,Test Park,Trial'
    return f'''<div class='race-venue'><h2>Test Park: Club<span class='race-venue-date'>Tuesday, 18 August 2026</span></h2></div>
Total Number of starters for this meeting (including emergencies) 1
<b>Results Last Published:</b> 18 August 2026<br><a href='#Race1'>1</a>
<table class='race-title'><tr><th>Race 1 - 9:00AM OPEN (800 METRES)</th></tr><tr><td><b>Time:</b> 0:48.90 <b>Last 600m:</b> 0:00.00 <b>Timing Method:</b> Electronic</td></tr></table>
<table class='race-strip-fields'><tr><th>Finish</th><th>No.</th><th>Horse</th><th>Trainer</th><th>Jockey</th><th>Margin</th><th>Bar.</th></tr>
<tr><td>1</td><td>1</td><td><a href='HorseFullForm.aspx?horsecode=synthetic&amp;Key={key}'>Synthetic Horse</a></td><td><a href='TrainerLastRuns.aspx?trainercode=t1'>Test Trainer</a></td><td><a href='JockeyLastRuns.aspx?jockeycode=j1'>Test Jockey</a></td><td></td><td>1</td></tr></table>'''.encode()

def test_official_clock_people_and_replay():
    d=parse(page(),ITEM,source_url(ITEM),NOW);r=d['rows'][0]
    assert r['heat_time_seconds']==48.9 and r['heat_last_600m_seconds'] is None
    assert r['jockey']=={'name':'Test Jockey','source_id':'j1'}
    c=sqlite3.connect(':memory:');c.executescript(SCHEMA);archive={'payload_hash':'synthetic','collected_at':NOW}
    assert install(c,d['rows'],archive)==1 and install(c,d['rows'],archive)==0
    with pytest.raises(sqlite3.IntegrityError):c.execute('DELETE FROM trial_official_observations')

@pytest.mark.parametrize('old,new',[(b'18 August 2026',b'19 August 2026'),(b'emergencies) 1',b'emergencies) 2'),(b'Electronic',b'Electronic INTERIM RESULTS'),(b'Test Park,Trial',b'Test Park,Race')])
def test_wrong_identity_incomplete_or_interim_sheet_is_rejected(old,new):
    with pytest.raises(MeetingError):parse(page().replace(old,new),ITEM,source_url(ITEM),NOW)

def test_access_challenge_is_explicit():
    with pytest.raises(MeetingError,match='source_access_challenge'):parse(b'<title>Are you human?</title>',ITEM,source_url(ITEM),NOW)
