<template>
  <v-card>
    <v-toolbar flat color="warning">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" />
        Confirm API key regeneration
      </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-card-text>
      This action will replace the existing api key with a new one.
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary
        color="warning"
        :loading="loading"
        :disabled="loading"
        @click="onDelete"
      >
        Regenerate key
      </v-btn-primary>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['regenerated', 'close'])
defineProps({ loading: Boolean })

const onDelete = () => {
  emit('regenerated')
}
</script>
