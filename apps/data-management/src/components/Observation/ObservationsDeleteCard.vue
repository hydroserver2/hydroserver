<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" />
        Confirm datastream data deletion
      </v-card-title>
    </v-toolbar>
    <v-card-text>
      This action will permanently delete all observations associated with this
      datastream but the actual datastream metadata will be preserved.
      <strong> ({{ datastream.name }}) </strong>
    </v-card-text>
    <v-card-text>
      Please type <strong> Delete </strong> to confirm deletion:
      <v-form>
        <v-text-field
          v-model="confirmationInput"
          @keydown.enter.prevent="onDelete"
        />
      </v-form>
    </v-card-text>
    <v-divider />
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-delete @click="onDelete">Confirm</v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { Snackbar } from '@/utils/notifications'
import { mdiAlert } from '@mdi/js'
import { ref } from 'vue'

const emit = defineEmits(['delete', 'close'])

const props = defineProps({
  datastream: {
    type: Object as () => any,
    required: true,
  },
})

const confirmationInput = ref('')

const onDelete = () => {
  if (confirmationInput.value.toLocaleLowerCase() !== 'delete') {
    Snackbar.error('inputs do not match')
    return
  }
  emit('delete')
  emit('close')
}
</script>
