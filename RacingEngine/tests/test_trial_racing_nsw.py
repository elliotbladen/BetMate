from pathlib import Path

from racing_engine.trial_racing_nsw import parse, source_url


def test_real_racing_nsw_page_is_source_shaped():
    payload = Path('/private/tmp/racing-nsw.html').read_bytes()
    item = {'date': '2026-09-10', 'venue': 'Lismore', 'isTrial': True, 'isJumpOut': False}
    result = parse(payload, item, source_url(item), '2026-09-15T00:00:00+00:00')
    assert len(result['rows']) == 15
    assert result['rows'][0]['distance_metres'] == 1010
    assert result['rows'][0]['heat_time_seconds'] == 60.39
    assert result['rows'][0]['source'] == 'racing_nsw'
