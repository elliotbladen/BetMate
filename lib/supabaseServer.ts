import { createClient } from '@supabase/supabase-js';

export function createServerClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  // Fail CLOSED. This previously returned a stub that answered [] to every query
  // and a null session to every auth check, with error: null - so a missing key
  // was indistinguishable from "no rows". That already produced a tipping dry run
  // reporting "0 people to remind" having queried nothing at all, and any caller
  // treating an empty result as a safe default was being handed a fabricated one.
  if (!url || !key) {
    throw new Error(
      'Supabase server client requires NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY. ' +
      'The anon key is public and belongs in .env.local for local development.'
    );
  }
  return createClient(url, key);
}

export async function getDataStore(key: string): Promise<unknown | null> {
  // Public display data only. A missing key degrades to null so the UI renders
  // empty rather than 500ing, but it is logged - never swallowed - so that
  // "no data on the site" is distinguishable from "Supabase is not configured".
  let supabase: ReturnType<typeof createServerClient>;
  try {
    supabase = createServerClient();
  } catch (err) {
    console.error(`getDataStore('${key}') could not reach Supabase:`, err);
    return null;
  }
  const { data, error } = await supabase
    .from('betmate_data_store')
    .select('data')
    .eq('key', key)
    .order('updated_at', { ascending: false })
    .limit(1);

  if (error || !data || data.length === 0) return null;
  return data[0].data;
}
