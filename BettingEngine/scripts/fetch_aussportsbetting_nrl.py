#!/usr/bin/env python3
"""
Download AusSportsBetting historical results and odds workbook.

The script discovers the Excel link from the public NRL historical data page,
downloads it, validates that it is an .xlsx workbook, then writes:

  outputs/nrl_weekly_review/historical/latest.xlsx
  outputs/nrl_weekly_review/historical/nrl_YYYYMMDD_HHMMSS.xlsx
  outputs/nrl_weekly_review/historical/latest.json

Scheduled by scripts/install_aussportsbetting_nrl_task.ps1 for Tuesday 09:00.

If the site blocks plain HTTP clients, the script falls back to Playwright.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import ssl
import sys
import tempfile
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_PATH = LOG_DIR / "aussportsbetting_nrl_download.log"
DEFAULT_PAGE_URL = "https://www.aussportsbetting.com/data/historical-nrl-results-and-odds-data/"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nrl_weekly_review" / "historical"
DEFAULT_PLAYWRIGHT_TIMEOUT_MS = 60_000
DEFAULT_PLAYWRIGHT_DOWNLOAD_MS = 90_000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

log = logging.getLogger("aussportsbetting_nrl")
_SSL_CONTEXT: ssl.SSLContext | None = None


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        text = " ".join(part.strip() for part in self._current_text if part.strip())
        self.links.append({"href": self._current_href, "text": text})
        self._current_href = None
        self._current_text = []


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def ssl_context() -> ssl.SSLContext:
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT

    context = ssl.create_default_context()
    if sys.platform == "win32" and hasattr(ssl, "enum_certificates"):
        for store_name in ("CA", "ROOT"):
            for cert_bytes, encoding, trust in ssl.enum_certificates(store_name):
                if encoding != "x509_asn":
                    continue
                if trust is True or "1.3.6.1.5.5.7.3.1" in trust:
                    try:
                        context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(cert_bytes))
                    except ssl.SSLError:
                        pass

    _SSL_CONTEXT = context
    return context


def fetch_bytes(url: str, timeout: int, allow_insecure_fallback: bool = True) -> tuple[bytes, str]:
    request = Request(url, headers=HEADERS)
    try:
        with urlopen(request, timeout=timeout, context=ssl_context()) as response:
            final_url = response.geturl()
            return response.read(), final_url
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        reason = exc.reason
        if (
            allow_insecure_fallback
            and url.lower().startswith("https://www.aussportsbetting.com/")
            and isinstance(reason, ssl.SSLCertVerificationError)
        ):
            log.warning("Verified HTTPS failed for %s; retrying AusSportsBetting with certificate checks disabled", url)
            insecure_context = ssl._create_unverified_context()
            with urlopen(request, timeout=timeout, context=insecure_context) as response:
                final_url = response.geturl()
                return response.read(), final_url
        raise RuntimeError(f"Network error while fetching {url}: {reason}") from exc


def discover_workbook_url(page_url: str, timeout: int) -> str:
    html_bytes, final_page_url = fetch_bytes(page_url, timeout)
    html = html_bytes.decode("utf-8", errors="replace")

    parser = LinkExtractor()
    parser.feed(html)

    candidates: list[str] = []
    for link in parser.links:
        href = link["href"]
        text = link["text"].lower()
        href_lower = href.lower()
        if href_lower.endswith(".xlsx"):
            candidates.append(urljoin(final_page_url, href))
        elif "2009" in text and "present" in text:
            candidates.append(urljoin(final_page_url, href))

    if not candidates:
        raise RuntimeError(f"Could not find the NRL workbook link on {page_url}")

    return candidates[0]


def validate_xlsx(path: Path) -> dict[str, object]:
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f"Downloaded file is not a valid .xlsx zip archive: {path}")

    with zipfile.ZipFile(path) as workbook:
        names = set(workbook.namelist())
        required = {"[Content_Types].xml", "xl/workbook.xml"}
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f"Downloaded .xlsx is missing required parts: {missing}")
        sheets = sorted(name for name in names if name.startswith("xl/worksheets/sheet"))

    return {
        "file_size_bytes": path.stat().st_size,
        "worksheet_count": len(sheets),
    }


def download_with_playwright(page_url: str, output_dir: Path, headless: bool) -> tuple[Path, str]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_dir / "download.tmp.xlsx"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            accept_downloads=True,
            ignore_https_errors=True,
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            log.info("Opening with Playwright: %s", page_url)
            page.goto(page_url, timeout=DEFAULT_PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            body_text = page.inner_text("body") if page.query_selector("body") else ""
            if any(marker in body_text for marker in ("FortiGuard", "Web Filter", "Access Blocked", "Web Page Blocked")):
                log.warning("Content filter page detected; attempting to click Proceed")
                proceed = None
                for selector in (
                    "a:has-text('Proceed')",
                    "button:has-text('Proceed')",
                    "input[value='Proceed']",
                    "a:has-text('proceed')",
                ):
                    proceed = page.query_selector(selector)
                    if proceed:
                        break
                if proceed is None:
                    raise RuntimeError(f"Content filter blocked page and no Proceed control was found: {body_text[:500]!r}")
                proceed.click()
                page.wait_for_timeout(4000)
                page.goto(page_url, timeout=DEFAULT_PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

            for selector in (
                "button:has-text('Accept All')",
                "button:has-text('Accept')",
                "a:has-text('Accept All')",
                "a:has-text('Accept')",
            ):
                cookie_button = page.query_selector(selector)
                if cookie_button:
                    log.info("Accepting cookie banner with selector: %s", selector)
                    cookie_button.click()
                    page.wait_for_timeout(1500)
                    break

            download_link = None
            for anchor in page.query_selector_all("a[href]"):
                href = anchor.get_attribute("href") or ""
                text = (anchor.text_content() or "").strip()
                href_lower = href.lower()
                if href_lower.endswith(".xlsx") or ".xlsx" in href_lower:
                    log.info("Found xlsx link: text=%r href=%s", text, href)
                    download_link = anchor
                    break
                if "2009" in text:
                    log.info("Found NRL 2009 link: text=%r href=%s", text, href)
                    download_link = anchor
                    break

            if download_link is None:
                body_text = page.inner_text("body")[:1000] if page.query_selector("body") else ""
                raise RuntimeError(f"Could not find NRL workbook link. Page text starts: {body_text!r}")

            with page.expect_download(timeout=DEFAULT_PLAYWRIGHT_DOWNLOAD_MS) as download_info:
                download_link.click()

            download = download_info.value
            download.save_as(str(temp_path))
            return temp_path, download.url
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Playwright timed out downloading AusSportsBetting workbook: {exc}") from exc
        finally:
            context.close()
            browser.close()


def download_workbook(
    page_url: str,
    output_dir: Path,
    timeout: int,
    playwright_fallback: bool,
    headless: bool,
) -> dict[str, object]:
    if not output_dir.is_absolute():
        output_dir = (ROOT / output_dir).resolve()
    else:
        output_dir = output_dir.resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = "nrl"
    if "historical-afl" in page_url.lower() or "afl.xlsx" in page_url.lower():
        stem = "afl"
    dated_path = output_dir / f"{stem}_{timestamp}.xlsx"
    latest_path = output_dir / "latest.xlsx"
    metadata_path = output_dir / "latest.json"
    method = "http"
    final_workbook_url = ""

    try:
        workbook_url = discover_workbook_url(page_url, timeout)
        log.info("Discovered workbook URL: %s", workbook_url)
        workbook_bytes, final_workbook_url = fetch_bytes(workbook_url, timeout)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir=output_dir) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(workbook_bytes)
    except Exception as exc:
        if not playwright_fallback:
            raise
        log.warning("HTTP download path failed; falling back to Playwright: %s", exc)
        tmp_path, final_workbook_url = download_with_playwright(page_url, output_dir, headless)
        method = "playwright"

    try:
        workbook_info = validate_xlsx(tmp_path)
        shutil.copy2(tmp_path, dated_path)
        shutil.move(str(tmp_path), latest_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    metadata = {
        "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        "source_page_url": page_url,
        "workbook_url": final_workbook_url,
        "method": method,
        "latest_path": str(latest_path.relative_to(ROOT)),
        "archived_path": str(dated_path.relative_to(ROOT)),
        **workbook_info,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    log.info("Saved latest workbook: %s", latest_path)
    log.info("Saved dated archive: %s", dated_path)
    log.info("Saved metadata: %s", metadata_path)
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download AusSportsBetting NRL 2009-present historical results and odds workbook."
    )
    parser.add_argument("--page-url", default=DEFAULT_PAGE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--no-playwright-fallback", action="store_true")
    parser.add_argument("--headless", default="true", help="Playwright fallback browser mode: true/false")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    try:
        metadata = download_workbook(
            page_url=args.page_url,
            output_dir=args.output_dir,
            timeout=args.timeout,
            playwright_fallback=not args.no_playwright_fallback,
            headless=args.headless.lower() != "false",
        )
    except Exception:
        log.exception("AusSportsBetting NRL workbook download failed")
        sys.exit(1)

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
