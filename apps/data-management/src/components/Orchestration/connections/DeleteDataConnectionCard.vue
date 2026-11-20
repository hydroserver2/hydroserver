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

    <v-card-text>
      Please type <strong>Delete</strong> to confirm deletion:
      <v-form>
        <v-text-field
          v-model="confirmationInput"
          :error-messages="confirmationError"
          @update:model-value="confirmationError = ''"
          @keydown.enter.prevent="onDelete"
        />
      </v-form>
    </v-card-text>
    <v-divider />
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-destructive @click="onDelete">Confirm</v-btn-destructive>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { mdiAlert } from '@mdi/js'
import { ref } from 'vue'

const emit = defineEmits(['delete', 'close'])
defineProps({ itemName: String })

const confirmationInput = ref('')
const confirmationError = ref('')

const onDelete = () => {
  if (confirmationInput.value.trim().toLowerCase() !== 'delete') {
    confirmationError.value = 'Type Delete to confirm deletion.'
    return
  }
  emit('delete')
  emit('close')
}
</script>
