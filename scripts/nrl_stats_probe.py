"""Extract and decode the NRL match centre's embedded SSR data blob."""
import html, re, requests, time, json

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,*/*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.nrl.com/draw/",
    "Origin": "https://www.nrl.com",
})
SESSION.get("https://www.nrl.com/draw/", timeout=15)
time.sleep(1)

url = "https://www.nrl.com/draw/nrl-premiership/2026/round-15/wests-tigers-v-titans/"
r = SESSION.get(url, timeout=25)
page = html.unescape(r.text)

# Look for all script blocks and find the one with the most stat-like content
script_blocks = re.findall(r'<script(?:\s[^>]*)?>(\{[\s\S]+?\})<\/script>', page)
print(f"JSON-looking script blocks: {len(script_blocks)}")

# Also look for window.* assignments
window_assigns = re.findall(r'window\.(\w+)\s*=\s*([\s\S]{50,5000}?);?\s*(?:window\.|</script>)', page)
for varname, varval in window_assigns:
    print(f"\n  window.{varname}: {varval[:200]}")

# Find context around "homeTotal" to understand what stats it represents
print("\n=== homeTotal/awayTotal context (500 chars each) ===")
for m in re.finditer(r'homeTotal', page):
    start = max(0, m.start() - 300)
    end = min(len(page), m.end() + 200)
    snippet = page[start:end]
    if '"label"' in snippet or '"name"' in snippet or '"stat"' in snippet or '"title"' in snippet:
        print(f"\n  [{m.start()}]")
        print(snippet)
        print()

# Find context around numerator/denominator
print("\n=== numerator/denominator context ===")
for m in re.finditer(r'"numerator"\s*:\s*36', page):  # 36 = Wests Tigers completions
    start = max(0, m.start() - 400)
    end = min(len(page), m.end() + 400)
    print(page[start:end])
    print()
    break

# Look for the team stats section specifically
print("\n=== teamStats or stats section ===")
for pattern in [r'"teamStats"\s*:', r'"team_stats"\s*:', r'"matchStats"\s*:', r'"aggregateStats"\s*:']:
    if re.search(pattern, page):
        m = re.search(pattern, page)
        start = m.start()
        print(f"\nFound '{pattern}' at pos {start}:")
        print(page[start:start+600])
