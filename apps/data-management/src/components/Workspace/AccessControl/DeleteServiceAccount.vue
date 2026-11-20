<template>
  <v-card>
    <v-toolbar flat color="delete">
      <v-card-title class="hs-subheading">
        <v-icon :icon="mdiAlert" />
        Confirm service account deletion
      </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-card-text>
      This action will permanently delete
      <strong> {{ itemName }} </strong>.
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-destructive :loading="loading" :disabled="loading" @click="onDelete">
        Delete
      </v-btn-destructive>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['delete', 'close'])
defineProps({ itemName: String, loading: Boolean })

const onDelete = () => {
  emit('delete')
}
</script>
