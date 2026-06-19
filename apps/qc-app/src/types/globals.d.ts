/// <reference types="vite/client" />

// Vuetify ships CSS via the `vuetify/styles` subpath. The package
// exports field maps it to a `.css` file with no accompanying `.d.ts`,
// so TypeScript can't resolve the import without an explicit
// declaration. Declared as a side-effect-only module since callers
// never read anything from it.
declare module 'vuetify/styles'

interface ImportMetaEnv {
  readonly VITE_APP_DISABLE_COOP?: string
  readonly VITE_APP_E2E_HOOKS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
