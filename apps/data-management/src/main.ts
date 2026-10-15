import '@/styles/tailwind.css'
import '@hydroserver/design-system/fonts.css'
import '@hydroserver/design-system/colors.css'
import '@hydroserver/design-system/layout.css'
import '@hydroserver/design-system/typography.css'
import '@hydroserver/design-system/components.css'
import 'ol/ol.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router/router'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import { createPinia } from 'pinia'
import { injectClarity } from '@/plugins/clarity'
import { injectGoogleAnalytics } from '@/plugins/googleAnalytics'
import { settings } from '@/config/settings'
import { startAppInitialization } from '@/bootstrap/appInitialization'

const app = createApp(App)
const pinia = createPinia()

function initializeApp() {
  app.use(pinia)

  // Start client initialization before the router's first navigation. The
  // router guard waits for the client, while the rest of the bootstrap can
  // finish after the app mounts.
  const initialization = startAppInitialization()

  app.use(router)
  app.use(vuetify)
  settings.analyticsConfiguration.enableClarityAnalytics &&
    settings.analyticsConfiguration.clarityProjectId &&
    injectClarity(settings.analyticsConfiguration.clarityProjectId)
  settings.analyticsConfiguration.enableGoogleAnalytics &&
    settings.analyticsConfiguration.googleAnalyticsMeasurementId &&
    injectGoogleAnalytics(
      settings.analyticsConfiguration.googleAnalyticsMeasurementId
    )
  app.mount('#app')

  return initialization
}

void initializeApp().catch((error) => {
  console.error('Error initializing app', error)
})
