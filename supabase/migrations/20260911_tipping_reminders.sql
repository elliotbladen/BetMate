-- One row per reminder actually sent, so a daily cron can run inside a multi-day
-- window without nagging the same person twice for the same gameweek.
create table if not exists public.tipping_reminders (
  reminder_id bigint generated always as identity primary key,
  comp_id uuid not null,
  user_id text not null,
  gameweek integer not null,
  sent_at timestamptz not null default now(),
  channel text not null default 'email' check (channel in ('email')),
  provider_id text,
  unique (comp_id, user_id, gameweek, channel)
);

create index if not exists tipping_reminders_gw_idx
  on public.tipping_reminders (comp_id, gameweek);

alter table public.tipping_reminders enable row level security;
-- No anon/authenticated policies: only the service role (the cron route) touches this.
