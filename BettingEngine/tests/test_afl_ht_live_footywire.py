from scripts.afl_ht_live import (
    load_q2_state,
    parse_footywire_stats_html,
    parse_fox_team_stats_html,
    save_q2_state,
)


def test_q2_state_survives_watcher_restart(tmp_path, monkeypatch):
    import scripts.afl_ht_live as live

    monkeypatch.setattr(live, "HALFTIME_DIR", tmp_path)
    expected = {"Port Adelaide vs Melbourne": {"timestr": "Q2 29:10", "complete": 49}}
    save_q2_state(2026, 23, expected)
    assert load_q2_state(2026, 23) == expected


def test_parse_footywire_head_to_head_cells():
    html = """
    <table id="headToHeadDiv">
      <tr><td class="statdata">23</td><td class="statdata">Inside 50s</td><td class="statdata">29</td></tr>
      <tr><td class="statdata">11</td><td class="statdata">Clearances</td><td class="statdata">23</td></tr>
      <tr><td class="statdata">27</td><td class="statdata">Clangers</td><td class="statdata">29</td></tr>
    </table>
    """
    assert parse_footywire_stats_html(html) == {
        "home_inside_50s": 23,
        "away_inside_50s": 29,
        "home_clearances": 11,
        "away_clearances": 23,
        "home_clangers": 27,
        "away_clangers": 29,
    }


def test_parse_footywire_ignores_incomplete_rows():
    html = '<tr><td class="statdata">Inside 50s</td></tr>'
    assert parse_footywire_stats_html(html) == {}


def test_parse_fox_player_stats_aggregates_team_totals():
    payload = {
        "hydration": {"page": {"content": {"widgets": {
            "playerstats-content-playerStats-0": {"playerStats$": {
                "team_A": {"players": [
                    {"stats": {"inside_fifty": 3, "clearances": 1, "errors": 4}},
                    {"stats": {"inside_fifty": 2, "clearances": 2, "errors": 1}},
                ]},
                "team_B": {"players": [
                    {"stats": {"inside_fifty": 4, "clearances": 3, "errors": 2}},
                ]},
            }}
        }}}}
    }
    html = (
        "<script>window.fisoBoot['core-match-centre']['x']="
        + __import__("json").dumps(payload)
        + ";</script>"
    )
    assert parse_fox_team_stats_html(html) == {
        "home_inside_50s": 5,
        "away_inside_50s": 4,
        "home_clearances": 3,
        "away_clearances": 3,
        "home_clangers": 5,
        "away_clangers": 2,
    }
