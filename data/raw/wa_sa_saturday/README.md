# WA/SA Saturday metropolitan archive

This directory covers Saturdays from **2023-09-18 through 2026-09-18** for
Ascot and Belmont Park (Perth) and Morphettville and Morphettville Parks
(Adelaide). `manifest.json` records the dated Racing Australia result request,
RaceHub race-1 request and RaceHub raceday request for every track/date, with
HTTP status, size and SHA-256. CAPTCHA/error responses are retained and marked
so they cannot be mistaken for race results.

`racehub_indexed_manifest.json` records the 462 individual RaceHub race pages
available from the four track indexes. Those pages contain the result fields
and RaceHub sectional data where indexed. The RaceHub track indexes do not
expose every historical meeting, and Racing Australia currently returns a
CAPTCHA challenge to unattended requests; therefore the archive is a complete
dated acquisition audit, but not yet a complete normalized three-year import.

`breednet/manifest.json` is the independent result fallback. It made 623/624
successful dated requests and found 197 full result pages, restoring barriers,
weights and beaten margins for meetings where the page exists. Breednet does
not publish the required sectional or steward-report fields. South Australian
official steward PDFs still need collection from Racing SA's dated S3/files
archive, and Western Australian race pages/reports from Racing WA/RWWA (whose
public endpoint rate-limits automated enumeration).
