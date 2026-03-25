<template>
  <router-view v-slot="{ Component }">
    <v-app>
      <Navbar
        v-if="Component && isHydroServerReady && !route.meta.hideNavBar"
      />

      <v-main>
        <component :is="Component" v-if="Component" />
        <v-container v-else-if="initializationError" class="fill-height">
          <v-row justify="center" align="center">
            <v-col cols="12" md="6" class="text-center">
              <h5 class="text-h5">Unable to load HydroServer</h5>
              <p class="mt-3 text-body-1">
                Check your connection and refresh the page.
              </p>
            </v-col>
          </v-row>
        </v-container>
        <FullScreenLoader v-else loading-text="Loading HydroServer..." />
      </v-main>

      <Footer v-if="Component && !route.meta.hideFooter" class="flex-grow-0" />
      <Notifications />
      <link
        href="https://fonts.googleapis.com/css?family=Roboto:100,300,400,500,700,900"
        rel="stylesheet"
      />
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
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<style lang="scss">
html {
  // Vuetify sets overflow-y to scroll by default. Therefore, we'll override to get rid
  // of the permanent scroll bar
  overflow-y: auto !important;
}
</style>
