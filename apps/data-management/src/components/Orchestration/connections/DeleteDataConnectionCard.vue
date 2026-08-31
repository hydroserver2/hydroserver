<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="hs-text-md">
        <v-icon :icon="mdiAlert" /> Confirm data connection deletion
      </v-card-title>
    </v-toolbar>

    <v-card-text>
      This action will permanently delete the data connection
      <strong> {{ itemName }} </strong>
      along with all tasks associated with it.
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-destructive @click="onDelete"> Delete </v-btn-destructive>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['delete', 'close'])
defineProps({ itemName: String })

const onDelete = () => {
  emit('delete')
  emit('close')
}
</script>
