-- Shadow-only map-position snapshots. No pricing/betting consumer is authorised.
create table if not exists public.racing_map_runner_predictions (
  id bigint generated always as identity primary key,
  model_version text not null,
  meeting_key text not null,
  race_number integer not null,
  runner_number integer not null,
  horse_name text not null,
  barrier integer,
  as_of timestamptz not null,
  field_hash text not null,
  probabilities jsonb not null,
  expected_settling_rank double precision,
  wide_risk double precision,
  slow_start_probability double precision,
  confidence double precision not null,
  simulation_seed bigint not null,
  information_cutoff timestamptz not null,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(model_version, meeting_key, race_number, runner_number, as_of)
);
create index if not exists racing_map_predictions_meeting_idx
  on public.racing_map_runner_predictions(meeting_key,race_number,as_of desc);

alter table public.racing_map_runner_predictions enable row level security;
revoke all on public.racing_map_runner_predictions from anon, authenticated;
