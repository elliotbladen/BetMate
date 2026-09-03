# Champions League Step 2 — data contract and club identity

The UCL data layer now requires canonical club IDs rather than raw names. Each
club record carries country, domestic league and validity dates so one club can
be linked across domestic and UEFA competitions without silently merging renamed
or reserve teams. Aliases must be unambiguous.

Each match requires a season, frozen competition stage, UTC kickoff, canonical
home/away IDs, score, source and source publication timestamp. The contract
rejects same-club fixtures, missing timezone information, negative scores and
unmapped aliases.

The supplied CSVs are empty templates. No historical club or match rows have
been fabricated. The next data task is to populate them from UEFA results and
domestic league sources, then validate coverage and identity collisions before
fitting ratings.
