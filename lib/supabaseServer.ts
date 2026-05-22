import { createClient } from '@supabase/supabase-js';

export function createServerClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}

export async function getDataStore(key: string): Promise<unknown | null> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from('betmate_data_store')
    .select('data')
    .eq('key', key)
    .limit(1);

  if (error || !data || data.length === 0) return null;
  return data[0].data;
}
