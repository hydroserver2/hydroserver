import '@/styles/global.scss'

import { createApp } from 'vue'
import store from '@/store'
import App from './App.vue'
import router from './router/router'
import vuetify from '@/plugins/vuetify'

const app = createApp(App)

app.use(store)
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

export default app
