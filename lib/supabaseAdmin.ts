import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * Service-role Supabase client. SERVER-ONLY — never import from a client component.
 *
 * lib/supabaseServer.ts deliberately uses the ANON key and is for user-scoped
 * reads. It also falls back to a no-op stub that answers `[]` to every query when
 * the anon key is absent, which is fine for a page but dangerous for a job: a cron
 * would "succeed" having found nobody. This client throws instead.
 *
 * Needed here because the reminder job must read auth.users for email addresses
 * and write tipping_reminders, neither of which the anon role can do.
 */
export function createAdminClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY?.trim();
  if (!url || !key) {
    throw new Error('Supabase admin client requires NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY');
  }
  return createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}
