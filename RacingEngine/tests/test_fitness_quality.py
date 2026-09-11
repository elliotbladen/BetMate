from RacingEngine.racing_engine.fitness_quality import quality_gate

def base(**extra):
    row = {"source":"rnsw", "source_event_id":"meeting-1-heat-1", "horse_id":"hrs_a", "event_date":"2026-09-01", "event_type":"official_trial", "finish_position":"1"}
    row.update(extra); return row

def test_identical_duplicate_collapses():
    result = quality_gate([base(), base()])
    assert result["accepted"] == 1 and result["identical_duplicates"] == 1

def test_conflicting_duplicate_quarantines():
    result = quality_gate([base(), base(finish_position="2")])
    assert result["accepted"] == 1 and result["quarantined"] == 1
    assert result["quarantined_rows"][0]["quality_reasons"] == ["conflicting_duplicate_payload"]

def test_missing_and_invalid_values_quarantine():
    result = quality_gate([base(source_event_id="", event_date="bad")])
    assert set(result["quarantined_rows"][0]["quality_reasons"]) == {"missing_source_event_id", "invalid_event_date"}
