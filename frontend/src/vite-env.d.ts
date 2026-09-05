/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin for production deployments. Empty in development (Vite proxy handles /api/*). */
  readonly VITE_API_BASE: string
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.css'
declare module '*.svg' {
  const src: string
  export default src
}
