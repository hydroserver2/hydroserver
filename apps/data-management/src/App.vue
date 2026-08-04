<template>
  <v-app>
    <Navbar v-if="!route.meta.hideNavBar" />

    <v-main :style="mainLayoutStyle">
      <router-view />
    </v-main>

    <Footer v-if="!route.meta.hideFooter" class="flex-grow-0" />
    <Notifications />
    <link
      href="https://fonts.googleapis.com/css?family=Roboto:100,300,400,500,700,900"
      rel="stylesheet"
    />
  </v-app>
</template>

<script setup lang="ts">
import Navbar from '@/components/base/Navbar.vue'
import Footer from '@/components/base/Footer.vue'
import Notifications from '@/components/base/Notifications.vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// Vuetify 4 can initially register a conditionally-rendered app bar with a
// zero layout height in optimized builds. Keep the shared main-content offset
// deterministic so the fixed navbar never covers page controls.
const mainLayoutStyle = computed(() => {
  const navbarHeight = route.meta.hideNavBar ? '0px' : '64px'
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
