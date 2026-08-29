from scripts.line_mover.scrape_team_lists import parse_afl_team_lists_html


def test_afl_parser_keeps_unchanged_team_and_maps_following_fixture():
    teams = [
        ("Fremantle", "Adelaide", ["A Pearce"], []),
        ("Richmond", "St Kilda", [], ["M Wood"]),
        ("North Melbourne", "Geelong", ["G Wardlaw"], ["J Martin"]),
        ("Brisbane", "Gold Coast", ["D Zorko"], ["J Farrar"]),
        ("Hawthorn", "Collingwood", ["K Amon"], ["H Harrison"]),
        ("Port Adelaide", "Melbourne", ["M Georgiades"], ["B Howes"]),
        ("GWS", "West Coast", ["J Riccardi"], []),
        ("Western Bulldogs", "Carlton", ["L McNeil"], []),
        ("Essendon", "Sydney", ["N Bryan"], ["L Melican"]),
    ]
    fixtures = []
    for home, away, home_ins, away_outs in teams:
        def side(ins=(), outs=()):
            return "<table><tr><td><b>Interchange</b></td></tr>" + "".join(
                ["<tr><td><b>Ins</b></td></tr>"]
                + [f"<tr><td>{p}</td></tr>" for p in ins]
                + ["<tr><td><b>Outs</b></td></tr>"]
                + [f"<tr><td>{p}</td></tr>" for p in outs]
            ) + "</table>"
        fixtures.append(
            f'<table><tr><td class="tbtitle">{home} v {away} (Venue)</td></tr>'
            f'<tr><td>{side(home_ins, [])}</td><td><table><tr><td>FB</td></tr></table></td>'
            f'<td>{side([], away_outs)}</td></tr></table>'
        )
    html = "<html><head><title>AFL 2026 Round 23 Team Selections</title></head><body>" + "".join(fixtures) + "</body></html>"

    result = parse_afl_team_lists_html(html)

    assert result["round"] == 23
    assert len(result["teams"]) == 18
    assert result["teams"]["West Coast Eagles"] == {"ins": [], "outs": []}
    assert result["teams"]["Western Bulldogs"]["ins"] == ["L McNeil"]
    assert result["teams"]["Sydney Swans"]["outs"] == ["L Melican"]
