from scripts.nrl_ht_live import (
    extract_halftime_stats,
    is_halftime,
    is_live,
    load_first_half_cache,
    save_first_half_cache,
)


def test_draw_feed_states_include_first_and_second_half():
    assert is_live({"matchState": "FirstHalf", "gameSeconds": 0})
    assert is_live({"matchState": "SecondHalf", "gameSeconds": 0})
    assert is_halftime({"matchState": "SecondHalf", "gameSeconds": 0})


def test_expanded_extraction_preserves_missing_territory():
    data = {
        "startTime": "2026-08-15T10:00:00Z",
        "homeTeam": {"teamId": 1, "name": "Home", "score": 6, "scoring": {}},
        "awayTeam": {"teamId": 2, "name": "Away", "score": 4, "scoring": {}},
        "stats": {"groups": [{"stats": [
            {"title": "Total Sets", "homeValue": {"value": 20}, "awayValue": {"value": 18}},
            {"title": "Line Breaks", "homeValue": {"value": 3}, "awayValue": {"value": 1}},
        ]}]},
        "timeline": [{"type": "Try", "teamId": 1, "gameSeconds": 500}],
    }
    stats = extract_halftime_stats(data, 2026, 24, 600)
    assert stats["home_ht_score"] == 6
    assert stats["home_total_sets"] == 20
    assert stats["away_line_breaks"] == 1
    assert stats["home_inside_20_possessions"] is None
    assert stats["snapshot_game_seconds"] == 600


def test_first_half_cache_survives_watcher_restart(tmp_path, monkeypatch):
    import scripts.nrl_ht_live as live

    monkeypatch.setattr(live, "HALFTIME_DIR", tmp_path)
    fixture = {
        "homeTeam": {"nickName": "Broncos"},
        "awayTeam": {"nickName": "Warriors"},
    }
    payload = {"gameSeconds": 2320, "stats": {"groups": []}}
    save_first_half_cache(24, fixture, payload, 2320)
    restored, observed = load_first_half_cache(24, fixture)
    assert restored == payload
    assert observed == 2320
