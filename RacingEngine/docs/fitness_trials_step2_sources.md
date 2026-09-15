# Fitness and trials engine — Step 2 source discovery

Status: **Step 2 complete; awaiting owner review**

This step maps the official Australian trial entry points before any downloader
or parser is built. It does not collect trial records yet.

## Source order

1. **Racing Australia** — national discovery and form aggregation. Its Service
   Centre describes selected trial-meeting support, so coverage must be measured
   rather than assumed to be complete: <https://racingaustralia.horse/AboutUs/ServiceCentre.aspx>
2. **Racing NSW** — official NSW trial fields and finalised trial pages. The
   public form pages expose trial metadata and may expose XML/CSV links:
   <https://mdata.racingnsw.com.au/FreeFields/Form.aspx?Key=2026Aug17%2CNSW%2CBathurst%2CTrial>
3. **Racing.com** — Victorian trial meeting cards/results where published, with
   sectional source documentation here:
   <https://www.racing.com/form> and
   <https://dxp-static.racing.com/sectionals/index.html>
4. **Licensed vendor fallback** — disabled until data rights, coverage and
   credentials are documented.

## Collection policy

The registry does not assume that any public page is an API. Step 3 will use
meeting-level discovery, cache raw responses, respect terms and rate limits, and
record the source URL, collection time, effective event time, parser version and
payload hash. Unresolved or conflicting records go to quarantine rather than
being silently merged.

The source registry is `config/fitness_trial_sources.json`. URL templates are
rendered only from discovered meeting values; the collector must not fabricate
trial result URLs.

## Coverage questions for Step 3

The downloader must measure, by state and date:

- trial meetings discovered;
- fields and final results available;
- times and sectionals available;
- durable provider IDs available;
- duplicate or conflicting source records;
- lag between trial time and publication.

No source is considered complete until those measurements are reported.
