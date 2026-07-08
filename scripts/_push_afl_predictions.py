import json, os, requests

for line in open('.env.local').readlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

url = os.environ['NEXT_PUBLIC_SUPABASE_URL'].rstrip('/')
key = os.environ['SUPABASE_SERVICE_ROLE_KEY']

predictions = json.load(open('data/afl/predictions/latest.json'))
payload = {'predictions': predictions}

resp = requests.post(
    f'{url}/rest/v1/betmate_data_store',
    headers={
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates',
    },
    data=json.dumps([{'key': 'afl_predictions', 'data': payload}]),
    timeout=15,
)
print(f'Push status: {resp.status_code}')

resp2 = requests.get(
    f'{url}/rest/v1/betmate_data_store?key=eq.afl_predictions&select=key,data',
    headers={'apikey': key, 'Authorization': f'Bearer {key}'},
    timeout=10,
)
rows = resp2.json()
print(f'Rows in Supabase: {len(rows)}')
if rows:
    preds = rows[0]['data']['predictions']
    print(f'Predictions count: {len(preds)}')
    for p in preds:
        print(f"  {p['homeTeam']} {p['predHomeScore']} vs {p['awayTeam']} {p['predAwayScore']}")
