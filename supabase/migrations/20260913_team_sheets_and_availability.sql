-- Team sheets and player availability for EPL, EFL, UCL and NFL.
--
-- DESIGN: this is a change-log, not a snapshot store. The betting value is not
-- "who is injured" - it is WHEN that became known, because team news is what moves
-- a line. A table holding only the current state answers the first question and
-- destroys the second, so every observation that DIFFERS from the last one is kept,
-- and identical re-observations are dropped on a fingerprint.
--
-- Same shape as odds_quote_changes, deliberately: that pattern is proven here, and
-- it means a future join across market moves and team news needs no translation.
--
-- ⚠️ LESSONS FROM 2026-09-12 BAKED IN:
--   * RLS is enabled on every table. Three tipping tables were created by hand in
--     the dashboard, went live with RLS OFF, and the public anon key could read and
--     write the lot. No table reaches production except through a migration.
--   * The unique constraints below are what any ignore-duplicates insert must name
--     in `on_conflict`. PostgREST resolves ignore-duplicates against the PRIMARY KEY
--     unless told otherwise, and these tables have generated-identity PKs which
--     never collide - so an insert that does not name the constraint will raise
--     23505 instead of skipping, exactly as odds_market_checkpoints did.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Capture runs. Mirrors odds_capture_runs, including 'skipped' - a cycle that
-- found nothing new must be distinguishable from one that never ran.
-- ---------------------------------------------------------------------------
create table if not exists public.team_news_capture_runs (
  run_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  worker_id text not null,
  status text not null check (status in ('running','success','partial','failed','skipped')),
  codes_requested text[] not null default '{}',
  codes_fetched text[] not null default '{}',
  fixtures_seen integer not null default 0,
  sheets_written integer not null default 0,
  availability_written integer not null default 0,
  errors jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

-- ---------------------------------------------------------------------------
-- Team sheets (football codes). One row per side per observed CHANGE.
-- ---------------------------------------------------------------------------
create table if not exists public.team_sheet_observations (
  observation_id bigint generated always as identity primary key,
  -- No ON DELETE clause: the two-word form lost its space in a paste and Postgres
  -- rejected "ondelete". Capture runs are never deleted, so the default (restrict)
  -- is the behaviour we want anyway.
  run_id uuid references public.team_news_capture_runs(run_id),
  captured_at timestamptz not null,
  code text not null check (code in ('EPL','EFL','UCL','NFL')),
  source text not null,
  source_match_id text not null,
  kickoff_utc timestamptz not null,
  minutes_to_kickoff integer not null,
  home_team text not null,
  away_team text not null,
  side text not null check (side in ('home','away')),
  team_name text not null,

  -- Stored VERBATIM from the source. FotMob degrades
  -- confirmed -> predicted -> lastStarting11 with distance from kickoff, and
  -- lastStarting11 is last week's team rather than a forecast. Flattening these
  -- into one "lineup" field would make a stale XI indistinguishable from a real
  -- prediction, which is the single easiest way to poison a model with this data.
  lineup_type text not null,
  formation text,
  starters jsonb not null default '[]'::jsonb,

  -- sha256 over (lineup_type, formation, ordered starter ids)
  value_fingerprint text not null,
  created_at timestamptz not null default now(),

  unique (source_match_id, side, value_fingerprint)
);

create index if not exists team_sheet_observations_fixture_idx
  on public.team_sheet_observations (code, kickoff_utc desc, source_match_id);

-- ---------------------------------------------------------------------------
-- Player availability. Covers football "unavailable" lists AND the NFL's
-- mandated practice report, which is why the status columns are nullable: the
-- codes report fundamentally different things and neither should be coerced into
-- the other's vocabulary.
-- ---------------------------------------------------------------------------
create table if not exists public.player_availability_observations (
  observation_id bigint generated always as identity primary key,
  -- No ON DELETE clause: the two-word form lost its space in a paste and Postgres
  -- rejected "ondelete". Capture runs are never deleted, so the default (restrict)
  -- is the behaviour we want anyway.
  run_id uuid references public.team_news_capture_runs(run_id),
  captured_at timestamptz not null,
  code text not null check (code in ('EPL','EFL','UCL','NFL')),
  source text not null,
  -- NOT NULL with an empty-string sentinel for club-level rows (the NFL report is
  -- not fixture-level). A nullable column here forced a coalesce() in the unique
  -- index, and PostgREST CANNOT target an expression index from an on_conflict
  -- column list - so every duplicate would have raised 23505 instead of being
  -- ignored, which is precisely the fault that cost eleven hours of odds
  -- collection on 2026-09-12.
  source_match_id text not null default '',
  kickoff_utc timestamptz,
  minutes_to_kickoff integer,
  team_name text not null,
  player_name text not null,
  source_player_id text,
  position text,

  reason_type text,                     -- injury | suspension | ...
  reason_detail text,                   -- "Knee", "Hamstring"

  -- Kept exactly as published. FotMob mixes a date band ("Mid October 2026") with
  -- a status word ("Doubtful") in this one field; parsing it to a timestamp at
  -- write time would invent precision the source never claimed and silently throw
  -- away the distinction between "back in three weeks" and "might play Saturday".
  expected_return_raw text,

  -- The importance rating AS IT STOOD ON THE DAY OF CAPTURE. Stamped once and
  -- never recomputed: if a squad player breaks out in March and is relabelled a
  -- star, an October injury being studied must still carry the October rating, or
  -- the study discovers a market "failure" to react to someone who was not yet a
  -- star. rating_as_of is what makes that auditable.
  star_rating smallint,
  rating_as_of date,

  practice_status text,                 -- NFL only: DNP / Limited / Full
  game_status text,                     -- NFL only: Out / Doubtful / Questionable

  value_fingerprint text not null,
  created_at timestamptz not null default now()
);

-- Plain column list so that an ignore-duplicates insert can name it verbatim in
-- on_conflict. This is the constraint the collector must pass:
--   on_conflict=code,team_name,player_name,source_match_id,value_fingerprint
create unique index if not exists player_availability_dedupe_idx
  on public.player_availability_observations
     (code, team_name, player_name, source_match_id, value_fingerprint);

create index if not exists player_availability_team_idx
  on public.player_availability_observations (code, team_name, captured_at desc);
create index if not exists player_availability_player_idx
  on public.player_availability_observations (code, player_name, captured_at desc);

-- ---------------------------------------------------------------------------
-- Access control. Deny by default; the collector writes with the service role,
-- which bypasses RLS. No policies are granted because nothing in the app reads
-- these yet - add one when a reader exists, not in advance.
-- ---------------------------------------------------------------------------
alter table public.team_news_capture_runs enable row level security;
alter table public.team_sheet_observations enable row level security;
alter table public.player_availability_observations enable row level security;
