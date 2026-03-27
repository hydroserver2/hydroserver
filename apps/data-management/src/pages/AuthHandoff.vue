<template>
  <v-container v-if="errorMessage" class="fill-height">
    <v-row justify="center" align="center">
      <v-col cols="12" md="6" class="text-center">
        <h5 class="text-h5">Unable to return to the app</h5>
        <p class="mt-3 text-body-1">{{ errorMessage }}</p>
        <v-btn class="mt-4" color="primary" @click="returnHome">Return home</v-btn>
      </v-col>
    </v-row>
  </v-container>
  <FullScreenLoader v-else loading-text="Returning to the app..." />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import router from '@/router/router'
import hs from '@hydroserver/client'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import { initializeAuthenticatedState } from '@/bootstrap/appInitialization'

const errorMessage = ref('')

function getReturnTo(): string {
  const rawReturnTo = new URLSearchParams(window.location.search).get('returnTo')
  if (!rawReturnTo) return '/'

  try {
    const normalized = new URL(rawReturnTo, window.location.origin)
    if (normalized.origin !== window.location.origin) {
      return '/'
    }
    return `${normalized.pathname}${normalized.search}${normalized.hash}` || '/'
  } catch {
    return '/'
  }
}

onMounted(async () => {
  const returnTo = getReturnTo()

  try {
    if (hs.session.isAuthenticated) {
      await initializeAuthenticatedState()
      await router.replace(returnTo)
      return
    }

    await hs.session.login(returnTo)
  } catch (error) {
    console.error('Error handing off account flow back to the app', error)
    errorMessage.value =
      error instanceof Error ? error.message : 'Please try signing in again.'
  }
})

async function returnHome() {
  await router.replace({ name: 'Browse' })
}
</script>
