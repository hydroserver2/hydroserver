<template>
  <router-view v-slot="{ Component }">
    <v-app>
      <Navbar v-if="Component && showNavBar" />

      <v-main :style="mainLayoutStyle">
        <component :is="Component" v-if="Component" />
        <HsEmptyState
          v-else-if="initializationError"
          title="Unable to load HydroServer"
        >
          Check your connection and refresh the page.
        </HsEmptyState>
        <HsFullScreenLoader v-else loading-text="Loading HydroServer..." />
      </v-main>

      <Footer v-if="Component && !route.meta.hideFooter" class="flex-grow-0" />
      <Notifications />
    </v-app>
  </router-view>
</template>

<script setup lang="ts">
import {
  initializationError,
  isHydroServerReady,
} from '@/bootstrap/appInitialization'
import Navbar from '@/components/base/Navbar.vue'
import Footer from '@/components/base/Footer.vue'
import Notifications from '@/components/base/Notifications.vue'
import {
  HsEmptyState,
  HsFullScreenLoader,
} from '@hydroserver/design-system/vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// The navbar waits for the client: it reads the session and the user's workspaces.
const showNavBar = computed(
  () => isHydroServerReady.value && !route.meta.hideNavBar
)

// Vuetify 4 can initially register a conditionally-rendered app bar with a
// zero layout height in optimized builds. Keep the shared main-content offset
// deterministic so the fixed navbar never covers page controls.
const mainLayoutStyle = computed(() => {
  const navbarHeight = showNavBar.value ? '64px' : '0px'
  return {
    '--v-layout-top': navbarHeight,
    paddingLeft: 'var(--v-layout-left, 0px)',
    paddingRight: 'var(--v-layout-right, 0px)',
    paddingTop: navbarHeight,
    paddingBottom: 'var(--v-layout-bottom, 0px)',
  }
})
</script>

<style lang="scss">
html {
  // Vuetify sets overflow-y to scroll by default. Therefore, we'll override to get rid
  // of the permanent scroll bar
  overflow-y: auto !important;
}
</style>
