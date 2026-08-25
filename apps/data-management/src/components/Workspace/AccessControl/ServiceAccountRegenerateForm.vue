<template>
  <v-card>
    <v-toolbar flat color="warning">
      <v-card-title class="hs-subheading">
        <v-icon :icon="mdiAlert" />
        Confirm service account API key regeneration
      </v-card-title>
    </v-toolbar>

    <v-card-text>
      This action will replace the existing service account API key with a new
      one.
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary :loading="loading" :disabled="loading" @click="onDelete">
        Regenerate key
      </v-btn-primary>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { mdiAlert } from '@mdi/js'

defineProps<{ loading?: boolean }>()
const emit = defineEmits(['regenerated', 'close'])

const onDelete = () => {
  emit('regenerated')
  emit('close')
}
</script>
