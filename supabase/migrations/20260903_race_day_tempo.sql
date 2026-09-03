-- Always-on Sydney/Melbourne race-day tempo collection and shadow snapshots.
create extension if not exists pgcrypto;

create table if not exists public.tempo_meetings (
  meeting_key text primary key,
  race_date date not null,
  state text not null check (state in ('NSW','VIC')),
  venue text not null,
  track_slug text not null,
  source_meeting_id text,
  source_url text,
  status text not null default 'scheduled' check (status in ('scheduled','live','complete','cancelled','source_pending')),
  first_race_at timestamptz,
  last_race_at timestamptz,
  discovered_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.tempo_races (
  race_key text primary key,
  meeting_key text not null references public.tempo_meetings(meeting_key),
  race_number integer not null,
  scheduled_start_at timestamptz,
  distance_metres integer,
  going_bucket text,
  rail_position text,
  group_grade integer,
  field_size integer,
  v0_probabilities jsonb,
  v0_scores jsonb,
  v0_model_version text,
  status text not null default 'scheduled' check (status in ('scheduled','due','sectionals_pending','observed','abandoned')),
  updated_at timestamptz not null default now(),
  unique (meeting_key,race_number)
);

create table if not exists public.tempo_source_polls (
  poll_id bigint generated always as identity primary key,
  meeting_key text references public.tempo_meetings(meeting_key),
  polled_at timestamptz not null default now(),
  source_name text not null,
  source_url text,
  http_status integer,
  payload_sha256 text,
  races_available integer not null default 0,
  status text not null check (status in ('success','pending','invalid','failed','skipped')),
  latency_ms integer,
  error text,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.tempo_race_observations (
  observation_id uuid primary key default gen_random_uuid(),
  race_key text not null references public.tempo_races(race_key),
  observed_at timestamptz not null default now(),
  source_name text not null,
  source_url text not null,
  source_published_at timestamptz,
  payload_sha256 text not null,
  sectional_runners integer not null,
  finished_runners integer not null,
  sectional_coverage numeric not null check (sectional_coverage between 0 and 1),
  early_seconds numeric not null,
  middle_seconds numeric not null,
  late_seconds numeric not null,
  early_score numeric,
  middle_score numeric,
  late_score numeric,
  quality_status text not null check (quality_status in ('accepted','partial','quarantined')),
  evidence jsonb not null default '{}'::jsonb,
  unique (race_key,payload_sha256)
);

create table if not exists public.tempo_shadow_snapshots (
  snapshot_id uuid primary key default gen_random_uuid(),
  snapshot_hash text not null unique,
  race_key text not null references public.tempo_races(race_key),
  meeting_key text not null references public.tempo_meetings(meeting_key),
  snapshot_version text not null,
  calculated_at timestamptz not null default now(),
  completed_races integer not null,
  same_regime_races integer not null,
  state_reliability numeric not null,
  v0_probabilities jsonb not null,
  shadow_probabilities jsonb not null,
  v0_scores jsonb not null,
  shadow_scores jsonb not null,
  update_status text not null check (update_status in ('v0','held','updated','condition_reset','insufficient_evidence')),
  reason_codes text[] not null default '{}',
  model_version text not null,
  policy_version text not null,
  horse_price_integration boolean not null default false,
  detail jsonb not null default '{}'::jsonb
);

create index if not exists tempo_races_due_idx on public.tempo_races(status,scheduled_start_at);
create index if not exists tempo_observations_race_idx on public.tempo_race_observations(race_key,observed_at);
create index if not exists tempo_snapshots_meeting_idx on public.tempo_shadow_snapshots(meeting_key,calculated_at);
create index if not exists tempo_polls_meeting_idx on public.tempo_source_polls(meeting_key,polled_at);

alter table public.tempo_meetings enable row level security;
alter table public.tempo_races enable row level security;
alter table public.tempo_source_polls enable row level security;
alter table public.tempo_race_observations enable row level security;
alter table public.tempo_shadow_snapshots enable row level security;

comment on table public.tempo_race_observations is 'Immutable official sectional observations; corrections append a new payload hash.';
comment on table public.tempo_shadow_snapshots is 'Append-only V0/V1/V2 tempo forecasts. Horse-price integration is hard-disabled.';
