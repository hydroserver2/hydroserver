<template>
  <v-container v-if="errorMessage" class="fill-height">
    <v-row justify="center" align="center">
      <v-col cols="12" md="6" class="text-center">
        <h5 class="text-h5">Unable to complete sign in</h5>
        <p class="mt-3 text-body-1">{{ errorMessage }}</p>
        <v-btn class="mt-4" color="primary" @click="returnHome">Return home</v-btn>
      </v-col>
    </v-row>
  </v-container>
  <FullScreenLoader v-else loading-text="Completing sign in..." />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import router from '@/router/router'
import hs from '@hydroserver/client'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import { initializeAuthenticatedState } from '@/bootstrap/appInitialization'

const errorMessage = ref('')

onMounted(async () => {
  try {
    const returnTo = await hs.session.completeLogin()
    await initializeAuthenticatedState()
    await router.replace(returnTo)
  } catch (error) {
    console.error('Error completing OIDC sign in', error)
    errorMessage.value =
      error instanceof Error ? error.message : 'Please try signing in again.'
  }
})

async function returnHome() {
  await router.replace({ name: 'Browse' })
}
</script>
