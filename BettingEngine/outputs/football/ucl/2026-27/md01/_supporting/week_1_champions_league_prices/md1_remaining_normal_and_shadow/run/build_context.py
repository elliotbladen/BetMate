"""Build the frozen, auditable research input for the six remaining MD1 fixtures.

Sources are archived under raw/. Nothing here invents a result, a date or a role:
football-data.co.uk supplies the domestic leagues it covers, Wikipedia + TheSportsDB
supply the Czech and Ukrainian leagues it does not, ESPN supplies squad position
groups, and UEFA supplies the matchday-1 possible line-ups and absence lists.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
from bs4 import BeautifulSoup

P = Path(__file__).parent
NOW = datetime.now(timezone.utc).isoformat()

UEFA = ('https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000'
        '--champions-league-predicted-line-ups-matchday-1-team-news-/')
UEFA_PUBLISHED = '2026-09-07T12:25:09Z'   # "Last updated: Monday, September 7, 2026"
FIXTURE_SOURCE = ('https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/'
                  'scoreboard?dates=20260909-20260913')
WIKI_CZE = 'https://en.wikipedia.org/wiki/2026%E2%80%9327_Czech_First_League'
WIKI_UKR = 'https://en.wikipedia.org/wiki/2026%E2%80%9327_Ukrainian_Premier_League'
TSDB = 'https://www.thesportsdb.com/api/v1/json/3/searchevents.php'

# UEFA news heading, football-data file, name in that file, model club id, ESPN roster file
TEAMS = [
    ('PSV',            'N1',     'PSV Eindhoven',  'psv',                   'roster_ned.1_148.json'),
    ('Shakhtar',       'manual', 'Shakhtar',       'fk-shakhtar-donetsk',   'roster_uefa.champions_493.json'),
    ('Fenerbahçe',     'T1',     'Fenerbahce',     None,                    'roster_tur.1_436.json'),
    ('Roma',           'I1',     'Roma',           'as-roma',               'roster_ita.1_104.json'),
    ('Bayern München', 'D1',     'Bayern Munich',  'fc-bayern-m-nchen',     'roster_ger.1_132.json'),
    ('Bodø/Glimt',     'NOR',    'Bodo/Glimt',     'fk-bod-glimt',          'roster_nor.1_2980.json'),
    ('Man United',     'E0',     'Man United',     'manchester-united-fc',  'roster_eng.1_360.json'),
    ('Sabah',          'none',   None,             None,                    'roster_uefa.champions_21922.json'),
    ('Slavia Praha',   'manual', 'Slavia Prague',  'sk-slavia-praha',       'roster_uefa.champions_494.json'),
    ('Lens',           'F1',     'Lens',           'racing-club-de-lens',   'roster_fra.1_175.json'),
    ('Como',           'I1',     'Como',           None,                    'roster_ita.1_2572.json'),
    ('Leipzig',        'D1',     'RB Leipzig',     'rb-leipzig',            'roster_ger.1_11420.json'),
]
DISPLAY = {'Bayern München': 'Bayern Munich', 'Bodø/Glimt': 'Bodo/Glimt', 'Man United': 'Manchester United',
           'Fenerbahçe': 'Fenerbahce', 'Slavia Praha': 'Slavia Prague', 'Shakhtar': 'Shakhtar Donetsk',
           'Leipzig': 'RB Leipzig', 'Sabah': 'Sabah FK', 'PSV': 'PSV Eindhoven', 'Roma': 'AS Roma'}

# Leagues football-data.co.uk does not publish. Scores and W/D/L come from the Wikipedia
# season articles and were reconciled against those pages' own league tables before use;
# individual match dates come from TheSportsDB event records.
MANUAL_RESULTS = {
    'Shakhtar Donetsk': dict(source=WIKI_UKR, date_source=TSDB, rows=[
        ('2026-08-02', 'Shakhtar Donetsk', 'Kudrivka', 5, 1, 'round_window_2026-07-31..2026-08-02'),
        ('2026-08-09', 'Epitsentr Kamianets-Podilskyi', 'Shakhtar Donetsk', 0, 2, 'exact'),
        ('2026-08-16', 'Kharkiv', 'Shakhtar Donetsk', 0, 1, 'exact'),
        ('2026-08-29', 'Shakhtar Donetsk', 'Polissya Zhytomyr', 0, 2, 'exact'),
        ('2026-09-05', 'Karpaty Lviv', 'Shakhtar Donetsk', 1, 2, 'exact')],
        table_check=dict(win=4, draw=0, loss=1, gf=10, ga=4, played=5)),
    'Slavia Prague': dict(source=WIKI_CZE, date_source=TSDB, rows=[
        ('2026-07-26', 'Slavia Prague', 'Slovácko', 5, 1, 'exact'),
        ('2026-08-01', 'Baník Ostrava', 'Slavia Prague', 0, 4, 'exact'),
        ('2026-08-09', 'Slavia Prague', 'Pardubice', 2, 1, 'exact'),
        ('2026-08-16', 'Slovan Liberec', 'Slavia Prague', 1, 1, 'exact'),
        ('2026-08-22', 'Slavia Prague', 'Bohemians 1905', 2, 2, 'exact'),
        ('2026-08-30', 'Sparta Prague', 'Slavia Prague', 0, 3, 'exact'),
        ('2026-09-05', 'Slavia Prague', 'Zbrojovka Brno', 4, 0, 'exact')],
        table_check=dict(win=5, draw=2, loss=0, gf=21, ga=5, played=7)),
}

FOOTBALL_DATA = {lg: (f'https://football-data.co.uk/new/{lg}.csv' if lg in ('NOR', 'AUT')
                      else f'https://football-data.co.uk/mmz4281/2627/{lg}.csv')
                 for lg in ['E0', 'I1', 'D1', 'F1', 'N1', 'T1', 'NOR']}

# ESPN publishes only broad squad groups (G/D/M/F). Each group maps to the generic
# member of the legacy football position weights; no specific tactical position is
# claimed for an absent player.
GROUP_ROLE = {'G': 'GK', 'D': 'CB', 'M': 'CM', 'F': 'FW'}
ROLE_NOTE = ('ESPN squad position group mapped to the generic within-group role; '
             'no tactical position claimed. A full-back absent from a "D" group is '
             'therefore priced with centre-back weights.')

# UEFA prints display names; ESPN squad names differ in accents/short forms.
NAME_OVERRIDES = {
    'Marlon Santos': 'Marlon', 'Mauro Júnior': 'Mauro Júnior', 'Man': 'Dennis Man',
    'Pléa': 'Alassane Pléa', 'Sildillia': 'Kiliann Sildillia', 'Ouaissa': 'Sami Ouaissa',
    'Lammers': 'Sam Lammers', 'Fesiun': 'Kiril Fesiun', 'Pedrinho': 'Pedrinho',
    'Guendouzi': 'Matteo Guendouzi', 'Oosterwolde': 'Jayden Oosterwolde', 'Asensio': 'Marco Asensio',
    'Pellegrini': 'Lorenzo Pellegrini', 'Gnabry': 'Serge Gnabry',
    'Aleesami': 'Haitam Aleesami', 'Evjen': 'Hakon Evjen', 'Mikkelsen': 'August Mikkelsen',
    'Riisnæs': 'Magnus Riisnaes', 'Hauge': 'Jens Petter Hauge', 'Gundersen': 'Jostein Gundersen',
    'Baleba': 'Carlos Baleba', 'De Ligt': 'Matthijs de Ligt', 'Diallo': 'Amad Diallo',
    'Heaton': 'Tom Heaton', 'Ugarte': 'Manuel Ugarte', 'Rashford': 'Marcus Rashford',
    'Holeš': 'Tomás Holes', 'Moses': 'David Moses', 'Ouanda': 'Adonija Bryan Ouanda',
    'Provod': 'Lukás Provod', 'Suleiman': 'Mubarak Suleiman', 'Zima': 'David Zima',
    'Baidoo': 'Samson Baidoo', 'Titraoui': 'Yassine Titraoui', 'Abdulhamid': 'Saud Abdulhamid',
    'Čelik': 'Nidal Celik', 'Gradit': 'Jonathan Gradit', 'Udol': 'Matthieu Udol',
    'Tobibo': None,   # not on the ESPN squad list; unresolved, recorded and not priced
    'Baumgartner': 'Christoph Baumgartner', 'Reitz': 'Rocco Reitz', 'Rômulo': 'Rômulo',
    'Gruda': 'Brajan Gruda',
}


def espn_squad(filename):
    payload = json.loads((P / 'raw' / filename).read_text())
    athletes = payload.get('athletes') or []
    if athletes and isinstance(athletes[0], dict) and 'items' in athletes[0]:
        athletes = [a for group in athletes for a in group['items']]
    return {a['displayName']: {'player_id': str(a['id']),
                               'group': (a.get('position') or {}).get('abbreviation'),
                               'jersey': a.get('jersey')} for a in athletes}


def uefa_sections():
    text = BeautifulSoup((P / 'raw/uefa_team_news.html').read_text(), 'html.parser')
    return text.get_text('\n', strip=True).replace('﻿', '')


def availability(name, text, squad, team_id_file):
    pattern = r'\n' + re.escape(name) + r'\nPossible line-up\n:(.*?)\nOut\n:(.*?)\nDoubtful\n:([^\n]*)'
    match = re.search(pattern, text, re.S)
    if not match:
        raise ValueError('Missing UEFA section for ' + name)
    lineup = [p.strip() for p in match.group(1).replace(';', ',').split(',') if p.strip()]
    events, unresolved = [], []
    for status, part in [('out', match.group(2)), ('doubtful', match.group(3))]:
        for item in part.strip().rstrip(',').split(','):
            item = item.strip()
            if not item or item.lower() == 'none':
                continue
            printed = item.split('(')[0].strip()
            squad_name = NAME_OVERRIDES.get(printed, printed)
            entry = squad.get(squad_name) if squad_name else None
            if entry is None or entry['group'] not in GROUP_ROLE:
                unresolved.append({'printed_name': printed, 'status': status, 'source_detail': item,
                                   'reason': 'no matching ESPN squad entry or position group'})
                continue
            events.append({'player': squad_name, 'printed_name': printed, 'player_id': entry['player_id'],
                           'status': status, 'espn_position_group': entry['group'],
                           'position': GROUP_ROLE[entry['group']], 'source_detail': item,
                           'source': UEFA, 'role_mapping': ROLE_NOTE,
                           'position_source': f'https://site.api.espn.com/apis/site/v2/sports/soccer/'
                                              f'{team_id_file.split("_")[1]}/teams/'
                                              f'{team_id_file.split("_")[2].split(".")[0]}/roster',
                           'retrieved_at_utc': NOW, 'source_published_at_utc': UEFA_PUBLISHED})
    conflicts = sorted({e['printed_name'] for e in events if e['printed_name'] in
                        {p.split('(')[0].strip() for p in lineup}})
    return events, lineup, unresolved, conflicts


def football_data_form(league, domestic, cutoff):
    frame = pd.read_csv(P / f'raw/{league}.csv').rename(
        columns={'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG'})
    frame['Date'] = pd.to_datetime(frame.Date, dayfirst=True, utc=True)
    frame = frame[(frame.Date >= '2026-07-01') & (frame.Date < cutoff)]
    frame = frame[(frame.HomeTeam == domestic) | (frame.AwayTeam == domestic)].sort_values('Date')
    rows = []
    for _, r in frame.iterrows():
        gf, ga = (r.FTHG, r.FTAG) if r.HomeTeam == domestic else (r.FTAG, r.FTHG)
        rows.append({'date': r.Date.date().isoformat(), 'home': r.HomeTeam, 'away': r.AwayTeam,
                     'home_goals': int(r.FTHG), 'away_goals': int(r.FTAG),
                     'points': 3 if gf > ga else 1 if gf == ga else 0,
                     'date_precision': 'exact', 'source': FOOTBALL_DATA[league]})
    return rows


def manual_form(team, cutoff):
    spec = MANUAL_RESULTS[team]
    rows = []
    for date, home, away, hg, ag, precision in spec['rows']:
        if pd.Timestamp(date, tz='UTC') >= cutoff:
            continue
        gf, ga = (hg, ag) if team in home else (ag, hg)
        rows.append({'date': date, 'home': home, 'away': away, 'home_goals': hg, 'away_goals': ag,
                     'points': 3 if gf > ga else 1 if gf == ga else 0,
                     'date_precision': precision, 'source': spec['source'],
                     'date_source': spec['date_source']})
    check = spec['table_check']
    got = dict(played=len(rows),
               win=sum(r['points'] == 3 for r in rows), draw=sum(r['points'] == 1 for r in rows),
               loss=sum(r['points'] == 0 for r in rows),
               gf=sum(r['home_goals'] if team in r['home'] else r['away_goals'] for r in rows),
               ga=sum(r['away_goals'] if team in r['home'] else r['home_goals'] for r in rows))
    if got != check:
        raise ValueError(f'{team} results do not reconcile with the published league table: {got} vs {check}')
    return rows


def main():
    cutoff = pd.Timestamp(NOW)
    text = uefa_sections()
    parsed = {}
    for name, league, domestic, club_id, roster_file in TEAMS:
        squad = espn_squad(roster_file)
        events, lineup, unresolved, conflicts = availability(name, text, squad, roster_file)
        if league == 'manual':
            results = manual_form(DISPLAY.get(name, name), cutoff)
            form_source = MANUAL_RESULTS[DISPLAY.get(name, name)]['source']
        elif league == 'none':
            results, form_source = [], None
        else:
            results = football_data_form(league, domestic, cutoff)
            form_source = FOOTBALL_DATA[league]
        window = results[-5:]
        parsed[DISPLAY.get(name, name)] = {
            'club_id': club_id, 'uefa_heading': name, 'league': league, 'domestic_name': domestic,
            'league_results': window, 'league_form_points': sum(r['points'] for r in window),
            'form_matches': len(window), 'season_league_matches_played': len(results),
            'latest_competitive_date': window[-1]['date'] if window else None,
            'form_source': form_source, 'rest_source': window[-1]['source'] if window else None,
            'availability': events, 'availability_unresolved': unresolved,
            'availability_lineup_conflicts': conflicts,
            'predicted_lineup': lineup, 'predicted_lineup_source': UEFA,
            'predicted_not_confirmed': True,
            'source_published_at_utc': UEFA_PUBLISHED, 'data_as_of_utc': NOW,
            'espn_roster_file': roster_file}

    fixtures = [
        ('Fenerbahce', 'AS Roma', '2026-09-10T16:45:00Z'),
        ('PSV Eindhoven', 'Shakhtar Donetsk', '2026-09-10T16:45:00Z'),
        ('Bayern Munich', 'Bodo/Glimt', '2026-09-10T19:00:00Z'),
        ('Como', 'RB Leipzig', '2026-09-10T19:00:00Z'),
        ('Manchester United', 'Sabah FK', '2026-09-10T19:00:00Z'),
        ('Slavia Prague', 'Lens', '2026-09-10T19:00:00Z'),
    ]
    rows = []
    for home, away, kickoff in fixtures:
        european = kickoff[:10]
        row = {'home': home, 'away': away, 'european_match_date': european,
               'sydney_match_date': str(pd.Timestamp(kickoff).tz_convert('Australia/Sydney').date()),
               'kickoff_utc': kickoff, 'matchday': 1,
               'referee': None, 'referee_status': 'No appointment published in any source consulted',
               'home_context': parsed[home], 'away_context': parsed[away]}
        for side in ('home_context', 'away_context'):
            context = row[side]
            latest = context['latest_competitive_date']
            context['rest_days'] = ((pd.Timestamp(european).date() - pd.Timestamp(latest).date()).days
                                    if latest else None)
            context['rest_basis'] = ('calendar days since the latest verified domestic league match; '
                                     'cup and European fixtures were checked and none fall later')
        rows.append(row)

    manifest = {
        'cutoff_utc': NOW,
        'status': 'researched_scenario_not_production_promotion',
        'matchday': 1, 'competition': 'UEFA Champions League 2026/27 league phase',
        'fixture_source': FIXTURE_SOURCE,
        'notes': [
            'Only current-season competitive domestic league matches enter form; friendlies, cups and European ties are excluded.',
            'For fewer than five league games, unplayed slots contribute neutral 1.5 points, an explicit shrinkage assumption, not invented match results.',
            'Rest is the calendar-date difference to the latest verified competitive club match; no claim of precise recovery hours.',
            'Czech and Ukrainian league results are unavailable from football-data.co.uk. They were taken from the Wikipedia season articles and reconciled against those articles\' own league tables (wins, draws, losses, goals for and against) before use; per-match dates come from TheSportsDB.',
            'Availability uses broad ESPN squad position groups mapped to generic legacy football position weights; it is not the trained UCL player shadow and does not value the individual player.',
            'Confirmed absences enter the central scenario. Doubtful and disputed players enter separate sensitivity scenarios.',
            'The UEFA possible line-ups and absence lists were last updated on 7 September 2026 and are three days older than this cutoff; UEFA was unreachable for a fresher pull (HTTP/2 INTERNAL_ERROR and timeouts).',
        ],
        'fixtures': rows,
        'raw_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted((P / 'raw').iterdir()) if p.is_file()},
    }
    (P / 'context.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'Saved {len(rows)} fixtures, {len(parsed)} teams')
    for name, context in parsed.items():
        print(f"  {name:22s} id={str(context['club_id']):24s} form={context['league_form_points']:>4}/"
              f"{context['form_matches']} latest={context['latest_competitive_date']} "
              f"rest={context.get('rest_days')} out/doubt={len(context['availability'])} "
              f"unresolved={len(context['availability_unresolved'])} conflicts={context['availability_lineup_conflicts']}")


if __name__ == '__main__':
    main()
