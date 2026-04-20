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

// TODO(oauth): re-enable OAuth sign-in once the qc-app is deployed
// somewhere the backend's OAuth app has registered as an authorized
// redirect URI. The provider list and icons are served from the
// backend's `<script id="app-settings">` (see `@/config/settings`),
// and the button click hands off to `hs.session.providerRedirect`,
// which issues a form POST that the backend answers with a 302 to
// Google. Google then redirects to whatever callback URL the backend's
// Google OAuth app has registered — that's the deployed playground
// origin, not `127.0.0.1:1203`. So clicking Google from local dev
// strands the user at the playground origin with a session cookie
// we can't read. Hidden until the deployment story makes the callback
// loop close back to this app.
const filteredOAuthProviders = computed<Provider[]>(() => [])

const signupOrLoginWithOAuth = (providerId: string) => {
  const callbackUrl = '/'
  hs.value.session.providerRedirect(providerId, callbackUrl, 'login')
}
</script>
