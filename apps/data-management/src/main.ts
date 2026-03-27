import '@/styles/tailwind.css'
import '@/styles/global.scss'
import 'ol/ol.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router/router'
import vuetify from '@/plugins/vuetify'
import pinia from '@/plugins/pinia'
import { injectClarity } from '@/plugins/clarity'
import { settings } from '@/config/settings'
import {
  startAppInitialization,
  waitForHydroServerInitialization,
} from '@/bootstrap/appInitialization'

const app = createApp(App)

app.use(pinia)

async function bootstrap() {
  // Kick off session initialization before router navigation starts, but do not
  // block first paint on the rest of the app bootstrap work.
  void startAppInitialization()
  await waitForHydroServerInitialization()

  app.use(router)
  app.use(vuetify)
  settings.analyticsConfiguration.enableClarityAnalytics &&
    settings.analyticsConfiguration.clarityProjectId &&
    injectClarity(settings.analyticsConfiguration.clarityProjectId)
  app.mount('#app')
}

void bootstrap()
