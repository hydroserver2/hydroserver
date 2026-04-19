import '@/styles/global.scss'

import { createApp } from 'vue'
import { storeToRefs } from 'pinia'
import store from '@/store'
import App from './App.vue'
import router from './router/router'
import vuetify from '@/plugins/vuetify'
import hs, { createHydroServer, User } from '@hydroserver/client'
import { useUserStore } from '@/store/user'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import { loadAppSettings } from '@/config/settings'

const app = createApp(App)

async function initializeApp() {
  app.use(store)

  // The session must be initialized before the router so auth guards
  // can read `hs.session.isAuthenticated` on the first navigation, and
  // so the user/workspace rehydration below has a live client to talk
  // to. Mirrors data-management-app/src/main.ts.
  //
  // Load runtime app-settings in parallel — auth provider config (the
  // Google/HydroShare OAuth button list) lives in the backend's index
  // HTML, not in the session endpoint. Running both at once keeps
  // boot latency flat.
  await Promise.all([
    createHydroServer({
      host:
        import.meta.env.VITE_APP_API_URL ||
        (import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''),
    }),
    loadAppSettings(),
  ])

  // Wire the singleton into the app's pre-existing pinia ref so every
  // `useHydroServer().hs` call site keeps working without churn.
  const { hs: hsRef } = storeToRefs(useHydroServer())
  hsRef.value = hs

  // Rehydrate the authenticated user. Suppress the expected 401 before
  // the user logs in by gating the request on the session snapshot.
  const { user } = storeToRefs(useUserStore())
  user.value = new User()
  if (hs.session.isAuthenticated) {
    const res = await hs.user.get()
    user.value = res.status === 401 ? new User() : res.data
  }

  // Pre-fetch workspaces when logged in so the picker renders without
  // a flash of emptiness. Skipped for anonymous boots — the Login page
  // doesn't read them.
  if (hs.session.isAuthenticated) {
    try {
      await useWorkspaceStore().loadWorkspaces()
    } catch (err) {
      console.error('Failed to load workspaces', err)
    }
  }

  app.use(router)
  app.use(vuetify)
  app.mount('#app')

  if (
    import.meta.env.DEV ||
    import.meta.env.VITE_APP_E2E_HOOKS === '1'
  ) {
    // Dynamic import keeps the chunk out of prod bundles even when the
    // static `import.meta.env.DEV` replacement path is rewritten by
    // mode-aware rollup configs. The import specifier is a literal
    // string so Vite can still resolve and code-split the module.
    import('./testHooks').then((m) => m.installTestHooks())
  }
}

initializeApp()

export default app
