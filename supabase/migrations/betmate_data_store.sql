-- betmate_data_store
-- Key-value store for scraped JSON data (BVI, team news, fixture, home/away).
-- Scrapers upsert into this table. API routes read from it.
-- Replaces local data/ file reads so the app works on Vercel.

create table if not exists betmate_data_store (
  key        text primary key,
  data       jsonb not null,
  updated_at timestamptz not null default now()
);

-- Allow anonymous reads (needed for anon key in API routes)
alter table betmate_data_store enable row level security;

create policy "Public read"
  on betmate_data_store
  for select
  using (true);

-- Writes require service role key (Python scrapers only)
-- No insert/update policy — service role bypasses RLS automatically
