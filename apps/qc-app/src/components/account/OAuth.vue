<template>
  <v-row justify="center" v-if="filteredOAuthProviders.length > 0">
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
    <v-col cols="auto" class="text-center"> OR </v-col>
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
  </v-row>

  <v-row v-for="provider in filteredOAuthProviders" :key="provider.id" justify="center">
    <v-col cols="12" sm="8" md="6">
      <v-btn
        @click="signupOrLoginWithOAuth(provider.id)"
        variant="outlined"
        color="primary"
        :rounded="false"
        block
        class="py-4"
      >
        <v-img
          :src="provider.iconLink || undefined"
          class="mr-1"
          width="100%"
          max-width="1.5rem"
          :alt="`${provider.name} icon`"
        />
        Continue with {{ provider.name }}
      </v-btn>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useHydroServer } from '@/store/hydroserver'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import type { Provider } from '@/models/settings'
const { hs } = storeToRefs(useHydroServer())

// TODO(oauth): re-enable once the qc-app deployment is registered as an
// authorized OAuth redirect URI. Local dev strands the user at the
// playground origin with a session cookie we can't read.
const filteredOAuthProviders = computed<Provider[]>(() => [])

const signupOrLoginWithOAuth = (providerId: string) => {
  const callbackUrl = '/'
  hs.value.session.providerRedirect(providerId, callbackUrl, 'login')
}
</script>
