# Trials release boundary

The trials database is released as two explicit populations:

* **Verified** rows have a deterministic registry link and evidence-backed
  event fields. They are the only rows available to production calculations.
* **Quarantined** rows remain in the append-only observation tables, but are
  excluded from production. Each row has a resolution status and source URL;
  unresolved identity, conflicting evidence, unavailable source results, and
  non-finish statuses are never silently discarded.

The reconciliation command is deliberately conservative. It links a row only
when the provider identity or a unique composite fingerprint agrees. A close
name without matching event evidence is not sufficient.

Before closing a data-ingestion change, run:

```sh
PYTHONPATH=RacingEngine \
python -m racing_engine.trial_data_reconcile \
  --database data/trials_review/nsw_archive/trials_review.sqlite \
  --registry-database data/racing_engine.sqlite \
  --report /tmp/trials_reconcile_report.json
```

The report must show `integrity_check: "ok"`, zero foreign-key violations,
and every observation assigned a resolution status. Non-zero unmatched or
conflicting counts are expected quarantine, not silently treated as verified
data.
