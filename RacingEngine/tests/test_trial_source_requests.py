import pytest
from urllib.error import HTTPError
from racing_engine.trial_source_requests import SourceGate,SourceAccessStopped,bounded_map

def test_access_denied_stops_subsequent_requests(tmp_path):
    gate=SourceGate(tmp_path/'block.json',interval=0);called=[]
    def denied():called.append(1);raise HTTPError('https://example.test',403,'Forbidden',{},None)
    with pytest.raises(SourceAccessStopped):gate.call(denied)
    with pytest.raises(SourceAccessStopped):gate.call(denied)
    assert called==[1] and 'HTTP_403' in (tmp_path/'block.json').read_text()

def test_html_challenge_is_not_treated_as_missing_data(tmp_path):
    gate=SourceGate(tmp_path/'block.json',interval=0)
    with pytest.raises(SourceAccessStopped):gate.call(lambda:b'<html><title>Are you human?</title></html>')

def test_bounded_map_does_not_submit_archive_after_failure():
    calls=[]
    def fail(n):calls.append(n);raise SourceAccessStopped('blocked')
    with pytest.raises(SourceAccessStopped):list(bounded_map(fail,range(100),workers=2))
    assert len(calls)<=2
