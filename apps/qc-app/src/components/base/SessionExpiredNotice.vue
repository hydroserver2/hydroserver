<template>
  <v-snackbar
    v-model="sessionExpired"
    :timeout="-1"
    color="warning"
    location="top"
    multi-line
    data-testid="session-expired"
  >
    Your login expired, so changes can't be saved. Your edits are still here.
    Log in again in a new tab, then try again.
    <template #actions>
      <v-btn variant="text" data-testid="session-expired-login" @click="logIn">
        Log in
      </v-btn>
      <v-btn
        variant="text"
        data-testid="session-expired-dismiss"
        @click="sessionExpired = false"
      >
        Dismiss
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useHydroServer } from '@/store/hydroserver'

const { hs, sessionExpired } = storeToRefs(useHydroServer())

// A new tab, so leaving the editor doesn't drop unsaved edits.
function logIn() {
  window.open(hs.value.session.getAccountLoginUrl('/qc/'), '_blank', 'noopener')
}
</script>
