-- Point-in-time market and news warehouse for AFL, NRL, EPL, EFL, NFL and UCL.
-- Apply before enabling cloud/odds_collector.py.

create extension if not exists pgcrypto;

create table if not exists public.odds_capture_runs (
  run_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  worker_id text not null,
  mode text not null check (mode in ('scheduled','event','checkpoint','close','dry_run')),
  status text not null check (status in ('running','success','partial','failed','skipped')),
  sports_requested text[] not null default '{}',
  sports_fetched text[] not null default '{}',
  api_requests_used integer not null default 0,
  api_requests_remaining integer,
  events_seen integer not null default 0,
  quotes_seen integer not null default 0,
  quote_changes_written integer not null default 0,
  errors jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.odds_quote_state (
  quote_key text primary key,
  sport text not null check (sport in ('AFL','NRL','EPL','EFL','NFL','UCL')),
  api_sport_key text not null,
  api_event_id text not null,
  commence_time timestamptz not null,
  home_team text not null,
  away_team text not null,
  bookmaker_key text not null,
  bookmaker_title text,
  bookmaker_updated_at timestamptz,
  market_key text not null check (market_key in ('h2h','spreads','totals','btts')),
  selection_key text not null check (selection_key in ('home','draw','away','over','under','yes','no')),
  selection_name text not null,
  line_value numeric,
  price_decimal numeric not null check (price_decimal >= 1.01),
  value_fingerprint text not null,
  first_seen_at timestamptz not null,
  last_seen_at timestamptz not null,
  last_changed_at timestamptz not null,
  source_region text,
  updated_at timestamptz not null default now()
);

create index if not exists odds_quote_state_event_idx
  on public.odds_quote_state (sport, api_event_id, market_key);
create index if not exists odds_quote_state_commence_idx
  on public.odds_quote_state (commence_time);

create table if not exists public.odds_quote_changes (
  quote_change_id bigint generated always as identity primary key,
  run_id uuid references public.odds_capture_runs(run_id) on delete set null,
  captured_at timestamptz not null,
  sport text not null check (sport in ('AFL','NRL','EPL','EFL','NFL','UCL')),
  api_sport_key text not null,
  api_event_id text not null,
  canonical_match_id bigint,
  commence_time timestamptz not null,
  home_team text not null,
  away_team text not null,
  bookmaker_key text not null,
  bookmaker_title text,
  bookmaker_updated_at timestamptz,
  market_key text not null check (market_key in ('h2h','spreads','totals','btts')),
  selection_key text not null check (selection_key in ('home','draw','away','over','under','yes','no')),
  selection_name text not null,
  line_value numeric,
  price_decimal numeric not null check (price_decimal >= 1.01),
  previous_line_value numeric,
  previous_price_decimal numeric,
  change_kind text not null check (change_kind in ('opening','price','line','line_and_price','checkpoint','closing')),
  checkpoint_name text,
  minutes_to_kickoff integer,
  source_region text,
  source_method text not null default 'odds_api',
  created_at timestamptz not null default now()
);

create index if not exists odds_quote_changes_event_time_idx
  on public.odds_quote_changes (sport, api_event_id, captured_at);
create index if not exists odds_quote_changes_market_idx
  on public.odds_quote_changes (sport, market_key, selection_key, captured_at);
create index if not exists odds_quote_changes_kickoff_idx
  on public.odds_quote_changes (commence_time);

create table if not exists public.odds_market_checkpoints (
  checkpoint_id bigint generated always as identity primary key,
  run_id uuid references public.odds_capture_runs(run_id) on delete set null,
  captured_at timestamptz not null,
  sport text not null check (sport in ('AFL','NRL','EPL','EFL','NFL','UCL')),
  api_event_id text not null,
  commence_time timestamptz not null,
  home_team text not null,
  away_team text not null,
  bookmaker_key text not null,
  market_key text not null,
  selection_key text not null,
  selection_name text not null,
  line_value numeric,
  price_decimal numeric not null check (price_decimal >= 1.01),
  checkpoint_name text not null,
  target_minutes_to_kickoff integer not null,
  actual_minutes_to_kickoff integer not null,
  bookmaker_updated_at timestamptz,
  created_at timestamptz not null default now(),
  unique (sport, api_event_id, bookmaker_key, market_key, selection_key, checkpoint_name)
);

create index if not exists odds_market_checkpoints_event_idx
  on public.odds_market_checkpoints (sport, api_event_id, checkpoint_name);

create table if not exists public.odds_sport_poll_state (
  sport text primary key check (sport in ('AFL','NRL','EPL','EFL','NFL','UCL')),
  api_sport_key text not null,
  enabled boolean not null default false,
  last_attempt_at timestamptz,
  last_success_at timestamptz,
  next_due_at timestamptz,
  nearest_kickoff timestamptz,
  consecutive_failures integer not null default 0,
  last_error text,
  api_requests_remaining integer,
  updated_at timestamptz not null default now()
);

create table if not exists public.market_news_events (
  news_event_id bigint generated always as identity primary key,
  published_at timestamptz not null,
  captured_at timestamptz not null default now(),
  sport text not null check (sport in ('AFL','NRL','EPL','EFL','NFL','UCL')),
  api_event_id text,
  canonical_match_id bigint,
  team_name text,
  player_name text,
  event_type text not null,
  status_before text,
  status_after text,
  position text,
  expected_role text,
  replacement_player text,
  source_level text not null check (source_level in ('A','B','C','D')),
  source_name text not null,
  source_url text not null,
  raw_text text,
  structured_summary text,
  confidence numeric check (confidence between 0 and 1),
  expected_impact numeric,
  confirmed boolean not null default false,
  content_hash text not null,
  supersedes_event_id bigint references public.market_news_events(news_event_id),
  created_at timestamptz not null default now(),
  unique (sport, content_hash)
);

create index if not exists market_news_events_match_time_idx
  on public.market_news_events (sport, api_event_id, published_at);
create index if not exists market_news_events_team_time_idx
  on public.market_news_events (sport, team_name, published_at);

create table if not exists public.odds_collection_alerts (
  alert_id bigint generated always as identity primary key,
  detected_at timestamptz not null default now(),
  resolved_at timestamptz,
  severity text not null check (severity in ('info','warning','critical')),
  sport text,
  alert_type text not null,
  message text not null,
  details jsonb not null default '{}'::jsonb,
  dedupe_key text not null,
  acknowledged boolean not null default false
);

create unique index if not exists odds_collection_alerts_open_dedupe_idx
  on public.odds_collection_alerts (dedupe_key) where resolved_at is null;

alter table public.odds_capture_runs enable row level security;
alter table public.odds_quote_state enable row level security;
alter table public.odds_quote_changes enable row level security;
alter table public.odds_market_checkpoints enable row level security;
alter table public.odds_sport_poll_state enable row level security;
alter table public.market_news_events enable row level security;
alter table public.odds_collection_alerts enable row level security;

-- No anon/authenticated policies are intentional. The cloud worker uses the
-- service-role key; public clients must use a curated server-side endpoint.

comment on table public.odds_quote_changes is
  'Append-only quote changes plus mandatory research checkpoints; never update or delete during the season.';
comment on table public.odds_quote_state is
  'Latest quote per bookmaker/market/selection identity, used to suppress unchanged duplicates.';

create or replace function public.betmate_market_storage_health()
returns jsonb
language sql
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'database_bytes', pg_database_size(current_database()),
    'database_mb', round(pg_database_size(current_database()) / 1024.0 / 1024.0, 2),
    'quote_state_rows', (select count(*) from public.odds_quote_state),
    'quote_change_rows', (select count(*) from public.odds_quote_changes),
    'checkpoint_rows', (select count(*) from public.odds_market_checkpoints),
    'news_rows', (select count(*) from public.market_news_events),
    'open_alerts', (select count(*) from public.odds_collection_alerts where resolved_at is null),
    'checked_at', now()
  );
$$;

revoke all on function public.betmate_market_storage_health() from public, anon, authenticated;
grant execute on function public.betmate_market_storage_health() to service_role;
