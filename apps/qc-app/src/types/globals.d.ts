/// <reference types="vite/client" />

// Vuetify ships CSS via the `vuetify/styles` subpath. The package
// exports field maps it to a `.css` file with no accompanying `.d.ts`,
// so TypeScript can't resolve the import without an explicit
// declaration. Declared as a side-effect-only module since callers
// never read anything from it.
declare module 'vuetify/styles'

interface ImportMetaEnv {
  readonly VITE_APP_VERSION: string
  readonly VITE_APP_API_URL?: string
  readonly VITE_APP_GOOGLE_MAPS_API_KEY?: string
  readonly VITE_APP_GOOGLE_OAUTH_ENABLED?: string
  readonly VITE_APP_ORCID_OAUTH_ENABLED?: string
  readonly VITE_APP_HYDROSHARE_OAUTH_ENABLED?: string
  readonly VITE_APP_DISABLE_ACCOUNT_CREATION?: string
  readonly VITE_APP_DISABLE_COOP?: string
  readonly VITE_APP_HS_USER?: string
  readonly VITE_APP_HS_PW?: string
  readonly VITE_APP_E2E_HOOKS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
