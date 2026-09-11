# Jockey and trainer data foundation audit

Date: 11 September 2026  
Branch: `feat/connections-engine-foundation`  
Status: audit only; no jockey/trainer effect has been added to ratings, map,
tempo, prices or bets

## Current coverage

The existing `runner_results` table covers 41,992 runner records from 12 August
2023 to 5 September 2026.

- Trainer is populated on all 41,992 rows.
- Jockey is populated on 40,355 rows (96.1%).
- The latest three-year window contains 40,911 trainer rows and 39,308 jockey
  rows.
- There are 351 raw jockey names and 916 raw trainer names.
- Basic normalisation identifies only three obvious trainer spelling variants;
  jockey names are already consistently formatted at this level.

The existing rows also carry race date, track, distance, going, barrier,
finish position, beaten margin and result status. That is enough to begin a
historical connections dataset.

## Current limitations

The database stores displayed names, not durable jockey or trainer provider
IDs. It does not yet preserve a point-in-time identity crosswalk, jockey claim
allowances, late jockey changes, trainer changes, or a separate source record
for each connection update. Raw result payloads contain the displayed names,
but they do not provide a stable identity contract.

Raw strike rates would also be misleading because jockey and trainer exposure
varies by track, distance, going, class, field strength and horse quality.

## Foundation work

The connections layer should add:

- durable provider ID crosswalks for jockeys and trainers;
- canonical display names and aliases;
- append-only identity changes and source provenance;
- final pre-jump jockey, trainer and claim state;
- race-context joins for track, distance, going, barrier and class;
- outcome labels for win, place, beaten margin and checkpoint position;
- minimum-sample and shrinkage fields;
- separate horse, jockey, trainer and jockey-trainer interaction keys.

The first engine should report context-adjusted evidence and uncertainty. It must
not treat a raw 30% strike rate from a small sample as a transferable effect.

## Next implementation steps

1. Build the identity crosswalk and normalise the three known trainer aliases.
2. Add audit checks for missing names, duplicate identities and impossible
   changes.
3. Build prior-only jockey and trainer feature tables by date.
4. Evaluate track, distance, going, class and field-size segments with shrinkage.
5. Add horse-specific and jockey-trainer interaction features only after the
   base effects are stable.
6. Keep the connections engine shadow-only until chronological tests show
   improvement over the horse-only baseline.
