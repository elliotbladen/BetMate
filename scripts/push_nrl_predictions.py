"""Push NRL round predictions to Supabase betmate_data_store key 'nrl_predictions'."""
import json, os, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
JSON_FILE = ROOT / "data" / "nrl" / "predictions" / "latest.json"
ENV = ROOT / ".env.local"

def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def push(predictions: list, url: str, key: str):
    payload = {"predictions": predictions}
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(
        f"{url}/rest/v1/betmate_data_store",
        headers=headers,
        json={"key": "nrl_predictions", "data": payload},
    )
    resp.raise_for_status()
    print(f"Pushed {len(predictions)} predictions -> Supabase key 'nrl_predictions' ({resp.status_code})")

if __name__ == "__main__":
    env = load_env()
    supabase_url = env.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        sys.exit("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env.local")

    predictions = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    push(predictions, supabase_url, service_key)
