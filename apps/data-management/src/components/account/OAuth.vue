<template>
  <v-row
    justify="center"
    v-if="filteredOAuthProviders.length > 0 && dividerPosition === 'top'"
  >
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
    <v-col cols="auto" class="text-center"> OR </v-col>
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
  </v-row>

  <v-row
    v-for="provider in filteredOAuthProviders"
    :key="provider.id"
    justify="center"
  >
    <v-col cols="12" :sm="fullWidth ? 12 : 8" :md="fullWidth ? 12 : 6">
      <v-btn
        type="button"
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

  <v-row
    justify="center"
    class="mb-2"
    v-if="filteredOAuthProviders.length > 0 && dividerPosition === 'bottom'"
  >
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
    <v-col cols="auto" class="text-center"> OR </v-col>
    <v-col cols="2">
      <v-divider class="mt-3" />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import hs from '@hydroserver/client'
import { computed, ref } from 'vue'
import { settings } from '@/config/settings'
import type { Provider } from '@/models/settings'
import { useRoute } from 'vue-router'
import { getPostLoginPath } from '@/utils/authRedirect'

withDefaults(
  defineProps<{
    fullWidth?: boolean
    dividerPosition?: 'top' | 'bottom'
  }>(),
  {
    fullWidth: false,
    dividerPosition: 'top',
  }
)

const oAuthProviders = ref<Provider[]>(
  settings.authenticationConfiguration.providers
)

const filteredOAuthProviders = computed(() =>
  oAuthProviders.value.filter((provider) => provider.signupEnabled)
)
const route = useRoute()
const postLoginPath = computed(() => getPostLoginPath(route.query.next))

const signupOrLoginWithOAuth = (providerId: string) => {
  const callbackUrl = postLoginPath.value
  hs.session.providerRedirect(providerId, callbackUrl, 'login')
}
</script>
