-- Product analytics event store. Writes are server-side only; reads are admin-only.
create table if not exists public.product_events (
  event_id uuid primary key default uuid_generate_v4(),
  event_name text not null check (event_name in (
    'page_view','page_exit','page_visibility_change','click','search_submitted',
    'filter_changed','market_selected','odds_card_expanded','baz_opened',
    'baz_question_submitted','baz_response_rendered','sign_in_started',
    'sign_in_completed','registration_started','registration_completed',
    'subscription_viewed','subscription_action'
  )),
  occurred_at_utc timestamptz not null,
  received_at_utc timestamptz not null default now(),
  session_id uuid not null,
  user_id uuid references auth.users(id) on delete set null,
  route text not null check (char_length(route) between 1 and 200),
  source_component text check (source_component is null or char_length(source_component) <= 100),
  metadata jsonb not null default '{}'::jsonb,
  duration_seconds integer check (duration_seconds is null or duration_seconds between 0 and 86400),
  device_class text check (device_class is null or device_class in ('mobile','tablet','desktop')),
  app_version text not null check (char_length(app_version) between 1 and 80),
  consent_state text not null check (consent_state in ('granted','denied','not_required'))
);

create index if not exists product_events_occurred_idx on public.product_events (occurred_at_utc desc);
create index if not exists product_events_route_idx on public.product_events (route, occurred_at_utc desc);
create index if not exists product_events_user_idx on public.product_events (user_id, occurred_at_utc desc);

alter table public.product_events enable row level security;

-- The API uses the service role after validation. No client insert policy exists.
drop policy if exists "Users read own product events" on public.product_events;
create policy "Users read own product events"
  on public.product_events for select
  using (auth.uid() = user_id);
