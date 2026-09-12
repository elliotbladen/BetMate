-- Make a second "opening" for the same quote impossible at the database level.
--
-- WHY. On 2026-09-12 the collector wrote 2,941 false openings across EPL, EFL and
-- NFL. Supabase.get_all() paged with Range offsets and no ORDER BY, so rows were
-- silently skipped between pages; a missed quote_key read as "never seen before",
-- which the collector records as change_kind='opening'. Only sports over the
-- 1000-row page size were affected — NFL 2,986 / EPL 2,094 / EFL 1,471 broke,
-- NRL 338 and AFL 248 never did.
--
-- The code bug is fixed (get_all now REQUIRES a stable order argument), and the
-- bad rows were repaired. This index is the part that does not depend on anyone
-- remembering: a quote opens exactly once, so the database should say so.
--
-- 'opening' is the reference price CLV is measured against. A false one does not
-- just duplicate — it replaces a real price move and loses the previous_* values
-- that make the move measurable. That is why this is worth a hard constraint
-- rather than a code comment.
--
-- PARTIAL index: it constrains only the 'opening' rows. Every other change_kind
-- can legitimately repeat for the same quote, and must stay free to.
--
-- BEFORE APPLYING, confirm the data is already clean — the index will refuse to
-- build otherwise, which is the correct behaviour but an unhelpful surprise:
--
--   select sport, count(*) - count(distinct (api_event_id, bookmaker_key,
--          market_key, selection_key)) as spurious
--   from public.odds_quote_changes
--   where change_kind = 'opening'
--   group by sport order by spurious desc;
--
-- Every row should read 0. If not, run cloud/repair_spurious_openings.py first.
--
-- If a future collector bug tries to write a duplicate opening, this raises 23505.
-- The collector records that in odds_capture_runs.errors and exits 0, so the cron
-- keeps its schedule — the failure is visible without being fatal.

create unique index if not exists odds_quote_changes_one_opening_idx
  on public.odds_quote_changes (sport, api_event_id, bookmaker_key, market_key, selection_key)
  where change_kind = 'opening';
