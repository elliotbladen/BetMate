import json,hashlib
from racing_engine.trial_coverage_report import duplicate_target

def test_empty_listing_requires_same_url_and_heat_subset(tmp_path):
    def report(code,heats,populated):
        payload=json.dumps({'data':{'getNoCacheRacesForMeet':[{'raceNumber':h,'formRaceEntries':[{'id':'synthetic'}] if populated else []} for h in heats]}}).encode()
        path=tmp_path/code;path.write_bytes(payload)
        return {'meeting':{'id':code,'date':'2026-08-01','state':'NSW','venue':'Test','meetUrl':'https://example.test/same','isTrial':True,'isJumpOut':False},'status':'imported' if populated else 'no_results_published','archive':{'payload_path':str(path),'payload_hash':hashlib.sha256(payload).hexdigest()}}
    empty=report('empty',[1,2],False);full=report('full',[1,2],True)
    assert duplicate_target(empty,[empty,full])==full
    full['meeting']['meetUrl']='https://example.test/other'
    assert duplicate_target(empty,[empty,full]) is None
    full=report('full',[1],True)
    assert duplicate_target(empty,[empty,full]) is None
