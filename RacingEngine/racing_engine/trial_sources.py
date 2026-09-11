"""Step 2 source registry for Australian thoroughbred trial ingestion."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "fitness_trial_sources.json"

def load_registry(path: Path = REGISTRY_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    source_ids = [row["source_id"] for row in data["sources"]]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate trial source_id")
    required = {"source_url", "collected_at", "effective_at", "parser_version", "payload_hash"}
    if set(data["policy"]["source_provenance_required"]) != required:
        raise ValueError("incomplete source provenance policy")
    return data

def render_form_url(source: dict, *, date: str, state: str, track: str) -> str:
    template = source.get("form_url_template")
    if not template:
        raise ValueError(f"source {source['source_id']} has no public form URL")
    return template.format(date=quote(date, safe=""), state=quote(state, safe=""), track=quote(track, safe=""))
