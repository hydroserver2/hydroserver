import '@/styles/tailwind.css'
import '@/styles/global.scss'
import 'ol/ol.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router/router'
import vuetify from '@/plugins/vuetify'
import { createPinia } from 'pinia'
import { injectClarity } from '@/plugins/clarity'
import { settings } from '@/config/settings'
import { startAppInitialization } from '@/bootstrap/appInitialization'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

// Kick off session initialization before router navigation starts, but do not
// block first paint on the rest of the app bootstrap work.
void startAppInitialization()

app.use(router)
app.use(vuetify)
settings.analyticsConfiguration.enableClarityAnalytics &&
  settings.analyticsConfiguration.clarityProjectId &&
  injectClarity(settings.analyticsConfiguration.clarityProjectId)
app.mount('#app')
