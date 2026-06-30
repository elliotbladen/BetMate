import { createClient } from '@supabase/supabase-js';

function createNoopServerClient() {
  return {
    auth: {
      async getSession() {
        return { data: { session: null }, error: null };
      },
      async exchangeCodeForSession() {
        return { data: null, error: new Error('Supabase is not configured in this local environment.') };
      },
    },
    from() {
      return {
        select() {
          return {
            eq() {
              return {
                order() {
                  return {
                    limit: async () => ({ data: [], error: null }),
                  };
                },
              };
            },
          };
        },
      };
    },
  };
}

export function createServerClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) return createNoopServerClient() as unknown as ReturnType<typeof createClient>;
  return createClient(
    url,
    key,
  );
}

export async function getDataStore(key: string): Promise<unknown | null> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from('betmate_data_store')
    .select('data')
    .eq('key', key)
    .order('updated_at', { ascending: false })
    .limit(1);

  if (error || !data || data.length === 0) return null;
  return data[0].data;
}
