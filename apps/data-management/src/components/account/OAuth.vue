<template>
  <v-row justify="center" v-if="oAuthProviders.length > 0">
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
    <v-col cols="auto" class="text-center"> OR </v-col>
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
  </v-row>

  <v-row v-for="provider in filteredOAuthProviders" justify="center">
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
import hs from '@hydroserver/client'
import { computed, ref } from 'vue'
import { settings } from '@/config/settings'
import type { Provider } from '@/models/settings'

const oAuthProviders = ref<Provider[]>(
  settings.authenticationConfiguration.providers
)

const filteredOAuthProviders = computed(() =>
  oAuthProviders.value.filter((provider) => provider.signupEnabled)
)

const signupOrLoginWithOAuth = (providerId: string) => {
  const callbackUrl = '/Sites'
  hs.session.providerRedirect(providerId, callbackUrl, 'login')
}
</script>
