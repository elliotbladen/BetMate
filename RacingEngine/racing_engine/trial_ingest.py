"""Step 3 meeting-level trial collector and deterministic HTML extractor."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

PARSER_VERSION = "fitness-trials-step3-v1"
USER_AGENT = "BetMate-FitnessResearch/1.0 (+source-respect; contact-owner)"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class _HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_anchor = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"] or "")
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("th", "td") and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def discover_trial_links(html: bytes, base_url: str) -> list[str]:
    parser = _HTMLTableParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    return sorted({urljoin(base_url, link) for link in parser.links if "trial" in link.lower()})


_ALIASES = {
    "horse": {"horse", "runner", "name"},
    "trainer": {"trainer", "trainers"},
    "jockey": {"jockey", "rider", "riders"},
    "barrier": {"barrier", "gate"},
    "distance": {"distance", "metres", "meters", "m"},
    "trial_type": {"trial type", "type", "race type", "heat type"},
    "position": {"position", "pos", "finish", "finish position", "result"},
    "margin": {"margin", "beaten", "beaten margin"},
    "time": {"time", "official time", "finish time"},
}


def _normalise_header(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


def extract_trial_rows(html: bytes, source_url: str) -> list[dict[str, str | None]]:
    parser = _HTMLTableParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    rows: list[dict[str, str | None]] = []
    for table in parser.tables:
        if not table:
            continue
        headers = [_normalise_header(value) for value in table[0]]
        mapping = {}
        for index, header in enumerate(headers):
            for canonical, aliases in _ALIASES.items():
                if header in aliases:
                    mapping[canonical] = index
        if "horse" not in mapping:
            continue
        for raw in table[1:]:
            if not raw or not raw[mapping["horse"]].strip():
                continue
            row = {key: (raw[index].strip() if index < len(raw) else None) for key, index in mapping.items()}
            row["source_url"] = source_url
            row["source_row_hash"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            rows.append(row)
    return rows


def archive_payload(archive_root: Path, *, source_id: str, source_url: str, payload: bytes,
                    collected_at: str | None = None) -> dict[str, object]:
    collected_at = collected_at or utc_now()
    digest = payload_hash(payload)
    target_dir = archive_root / source_id / digest[:2]
    target_dir.mkdir(parents=True, exist_ok=True)
    payload_path = target_dir / f"{digest}.html"
    metadata_path = target_dir / f"{digest}.json"
    if not payload_path.exists():
        payload_path.write_bytes(payload)
    metadata = {
        "source_id": source_id, "source_url": source_url, "collected_at": collected_at,
        "parser_version": PARSER_VERSION, "payload_hash": digest,
        "payload_path": str(payload_path),
    }
    if not metadata_path.exists():
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def fetch(url: str, timeout: int = 30) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def collect_explicit_urls(source_id: str, urls: list[str], archive_root: Path,
                          fetcher=fetch) -> dict[str, object]:
    pages = []
    for url in urls:
        try:
            body = fetcher(url)
            metadata = archive_payload(archive_root, source_id=source_id, source_url=url, payload=body)
            rows = extract_trial_rows(body, url)
            links = discover_trial_links(body, url)
            pages.append({**metadata, "status": "ok", "row_count": len(rows), "trial_links": links})
        except Exception as exc:  # retain failure evidence for retry/audit
            pages.append({"source_id": source_id, "source_url": url, "collected_at": utc_now(),
                          "parser_version": PARSER_VERSION, "status": "error", "error": str(exc)})
    return {"manifest_version": "fitness-trials-step3-manifest-v1", "source_id": source_id,
            "parser_version": PARSER_VERSION, "pages": pages}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect explicitly supplied trial pages")
    parser.add_argument("--source", required=True)
    parser.add_argument("--url", action="append", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = collect_explicit_urls(args.source, args.url, args.archive)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source_id": args.source, "pages": len(result["pages"]),
                      "ok": sum(page["status"] == "ok" for page in result["pages"])}, indent=2))


if __name__ == "__main__":
    main()
