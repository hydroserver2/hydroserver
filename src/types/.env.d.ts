/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_VERSION: string
  readonly VITE_APP_GOOGLE_MAPS_API_KEY: string
  readonly VITE_APP_GOOGLE_OAUTH_ENABLED: string
  readonly VITE_APP_ORCID_OAUTH_ENABLED: string
  readonly VITE_APP_HYDROSHARE_OAUTH_ENABLED: string
  readonly VITE_APP_E2E_HOOKS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}