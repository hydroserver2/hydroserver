<template>
  <v-btn
    v-if="isLoaded"
    color="deep-orange"
    :prepend-icon="mdiLink"
    @click="manageHydroShareConnection"
  >
    Manage HydroShare connection
  </v-btn>
</template>

<script setup lang="ts">
import { useHydroShare } from '@/composables/useHydroShare'
import { mdiLink } from '@mdi/js'

const { isLoaded, manageHydroShareConnection } = useHydroShare()
</script>
