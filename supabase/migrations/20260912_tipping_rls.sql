-- ###########################################################################
-- ##  SAFE TO APPLY. The companion code change is already done.            ##
-- ###########################################################################
--
-- This was NOT safe until commit-time today. The tipping routes used to query
-- through lib/supabaseServer.ts createServerClient(), which is the ANON key with
-- no cookies forwarded - it carries no user identity, so auth.uid() evaluated to
-- NULL in every query it made. Enabling the policies below against that would
-- have matched nothing: empty leaderboard, no tips, vanished entries.
--
-- All five call sites now use createAdminClient() (service role) instead:
--   app/api/tipping/{tips,join,leaderboard,results}/route.ts
--   lib/tippingResults.ts
--
-- That is the shape the codebase already used in app/api/cron/tipping-reminder.
-- The route authenticates the caller with getAuthenticatedUser(), decides what
-- they are allowed to see, and only then queries with a privileged client.
--
-- Because the service role BYPASSES the policies below, the route's own checks
-- stay load bearing. The policies are the second line of defence: they stop the
-- public anon key - which ships in every browser - reaching this data directly,
-- whatever the routes do or later get refactored into.
--
-- STILL RUN THIS FIRST, to see what you are changing from:
--
--   select relname, relrowsecurity from pg_class
--   where relname in ('tipping_comps','tipping_entries','tipping_tips');
--
-- If a table already reads true, check its existing policies before applying -
-- `create policy` fails on a duplicate name, and the `drop policy if exists`
-- lines below only clear the names used here.
--
-- AFTER APPLYING, exercise the tipping flow end to end: join a comp, submit
-- tips, load the leaderboard.
--
-- ###########################################################################

-- Row Level Security for the tipping tables.
--
-- These three tables were created by hand in the Supabase dashboard and appear in
-- no migration, so their access control could not be established from the repo.
-- Every other table in this directory carries an explicit `enable row level
-- security`; these did not. The API queries them with the ANON key
-- (lib/supabaseServer.ts), which is public in every browser - so without RLS the
-- whole tipping dataset is readable and writable directly against PostgREST,
-- bypassing the API and every check inside it.
--
-- BEFORE APPLYING, establish the current state:
--
--   select relname, relrowsecurity from pg_class
--   where relname in ('tipping_comps','tipping_entries','tipping_tips');
--
-- If relrowsecurity is already true for a table, check its existing policies
-- before adding these - `create policy` fails on a duplicate name, and the
-- `drop policy if exists` lines below only clear the names used here.
--
-- AFTER APPLYING, exercise the tipping flow end to end. Anything that breaks was
-- relying on the absence of these controls.

-- ---------------------------------------------------------------------------
-- tipping_comps - competition metadata. Readable by any signed-in user (they
-- need it to browse and join); only the creator may change it.
-- ---------------------------------------------------------------------------
alter table public.tipping_comps enable row level security;

drop policy if exists "Signed-in users read comps" on public.tipping_comps;
create policy "Signed-in users read comps"
  on public.tipping_comps for select
  to authenticated
  using (true);

drop policy if exists "Creator updates own comp" on public.tipping_comps;
create policy "Creator updates own comp"
  on public.tipping_comps for update
  to authenticated
  using (auth.uid() = created_by)
  with check (auth.uid() = created_by);

-- ---------------------------------------------------------------------------
-- tipping_entries - who is in which competition. The leaderboard needs every
-- entry in a comp to be visible, so reads stay open to signed-in users; a user
-- may only create or modify their OWN entry, which is what stops someone
-- inserting themselves under another name or editing a rival's points.
-- ---------------------------------------------------------------------------
alter table public.tipping_entries enable row level security;

drop policy if exists "Signed-in users read entries" on public.tipping_entries;
create policy "Signed-in users read entries"
  on public.tipping_entries for select
  to authenticated
  using (true);

drop policy if exists "Users insert own entry" on public.tipping_entries;
create policy "Users insert own entry"
  on public.tipping_entries for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists "Users update own entry" on public.tipping_entries;
create policy "Users update own entry"
  on public.tipping_entries for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- tipping_tips - the selections themselves.
--
-- READ is deliberately restricted to your own tips at the database level. Tips
-- becoming visible to everyone once a gameweek locks is an intended product
-- feature, but "is this gameweek locked" is not a fact this table holds - kickoff
-- times live in lib/tipping.ts, not in Postgres - so RLS cannot express it. The
-- post-lock reveal therefore stays an API concern, served by the service-role
-- client which bypasses RLS, with the lock check done in the route.
--
-- The effect: the anon key can never read another user's tips at any time, and
-- the API decides when the reveal is legitimate. Defence in depth rather than
-- the route being the only thing standing in the way.
-- ---------------------------------------------------------------------------
alter table public.tipping_tips enable row level security;

drop policy if exists "Users read own tips" on public.tipping_tips;
create policy "Users read own tips"
  on public.tipping_tips for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists "Users insert own tips" on public.tipping_tips;
create policy "Users insert own tips"
  on public.tipping_tips for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists "Users update own tips" on public.tipping_tips;
create policy "Users update own tips"
  on public.tipping_tips for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- No delete policy anywhere: nothing in the app deletes tips, entries or comps,
-- and a policy that does not exist cannot be exploited. Add one when a feature
-- actually needs it.
