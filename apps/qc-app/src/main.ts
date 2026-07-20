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
import { ensureCalibration } from '@uwrl/qc-utils'

const app = createApp(App)

async function initializeApp() {
  app.use(store)

  const hydroServerHost =
    import.meta.env.VITE_APP_PROXY_BASE_URL
      ? ''
      : import.meta.env.DEV
      ? 'http://127.0.0.1:8000'
      : ''

  // The session must be initialized before the router so auth guards
  // can read `hs.session.isAuthenticated` on the first navigation, and
  // so the user/workspace rehydration below has a live client to talk
  // to. Mirrors data-management-app/src/main.ts.
  //
  await createHydroServer({ host: hydroServerHost })

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
    user.value = res.ok && res.status !== 401 ? res.data : new User()
  }

  // Pre-fetch workspaces when logged in so the picker renders without
  // a flash of emptiness.
  if (hs.session.isAuthenticated) {
    try {
      await useWorkspaceStore().loadWorkspaces()
    } catch (err) {
      console.error('Failed to load workspaces', err)
    }
  }

  // Honour a shared-link `?ws=<id>` on initial page load. Runs before
  // `app.mount` so App.vue's first catalog load targets the right
  // workspace; the mount-time load races the router guard's switch
  // and can leave the user on the stored workspace otherwise.
  // `applyWorkspaceById` falls back to a placeholder when the full
  // record isn't available yet, which matters in cross-origin dev
  // setups where `loadWorkspaces` is skipped.
  try {
    const params = new URLSearchParams(window.location.search)
    const urlWorkspace = params.get('ws')
    if (urlWorkspace) {
      useWorkspaceStore().applyWorkspaceById(urlWorkspace)
    }
  } catch (err) {
    console.warn('Failed to apply URL workspace override', err)
  }

  app.use(router)
  app.use(vuetify)
  app.mount('#app')

  // Run qc-utils' worker/inline calibration when the browser is idle so
  // the crossover thresholds match this device. Results are cached in
  // `localStorage`; the "Recalibrate" button in the nav rail can force
  // a rerun. Non-critical — failures just fall back to conservative
  // defaults baked into qc-utils.
  const kickoffCalibration = () => {
    ensureCalibration().catch((err) => {
      console.warn('qc-utils calibration failed', err)
    })
  }
  if (typeof (window as any).requestIdleCallback === 'function') {
    ;(window as any).requestIdleCallback(kickoffCalibration, { timeout: 2000 })
  } else {
    setTimeout(kickoffCalibration, 500)
  }

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
