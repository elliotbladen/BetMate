# UCL alternate xG recovery audit

FotMob public match-detail records were matched to all 36 quarantined fixtures
using season, club pair and final score. Each record exposed a shotmap with
expected-goals values and was aggregated by home/away team.

- Recovered: **36/36**
- Shotmap coverage flag: **xG** for all recovered records
- Duplicate FotMob match IDs: **0**
- Combined recent dataset: **378/378** matches

The combined file is explicitly a **mixed-provider sensitivity track**:
342 SofaScore shotmap rows and 36 FotMob shotmap rows. It must not replace the
SofaScore-only primary dataset until a provider-scale calibration check is run.
