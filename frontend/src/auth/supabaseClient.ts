/**
 * Supabase JS client singleton for the frontend.
 *
 * Uses the frontend-safe ANON key only — the service role key
 * is never exposed to the browser.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl: string = (import.meta.env.VITE_SUPABASE_URL as string) ?? ''
const supabaseAnonKey: string = (import.meta.env.VITE_SUPABASE_ANON_KEY as string) ?? ''

// Warn in console rather than throwing — prevents blank screen if env vars
// are missing at build time. Auth calls will fail gracefully with a clear error.
if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    '[Supabase] Missing environment variables: VITE_SUPABASE_URL and/or VITE_SUPABASE_ANON_KEY. ' +
    'Add them to your Vercel project settings under Environment Variables.'
  )
}

/**
 * Singleton Supabase client.
 *
 * persistSession: true  — allows Supabase to store the session in localStorage
 *                         so sign-in actually works and survives page refresh.
 * autoRefreshToken: true — keeps the session alive automatically.
 * detectSessionInUrl: true — handles OAuth & magic-link callbacks.
 */
export const supabase: SupabaseClient = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder-key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
)
