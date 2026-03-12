<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" />
        Confirm unlinking HydroShare archival
      </v-card-title>
    </v-toolbar>

    <v-card-text>
      This action will permanently delete any archival configurations you have
      set for this site and stop any scheduled archival. Related files in
      HydroShare will remain unaffected.
    </v-card-text>

    <v-card-text>
      Please type the following text to confirm deletion:
      <strong>unlink archival</strong>
      <v-form>
        <v-text-field
          v-model="deleteInput"
          solo
          @keydown.enter.prevent="deleteLink"
        ></v-text-field>
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="cancelDeletion">Cancel</v-btn-cancel>
      <v-btn-delete @click="deleteLink">Delete</v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { Snackbar } from '@/utils/notifications'
import { ref } from 'vue'
import hs from '@hydroserver/client'
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['delete', 'close'])
const props = defineProps({
  thingId: { type: String, required: true },
})
const deleteInput = ref('')

async function deleteLink() {
  if (deleteInput.value.toLowerCase() !== 'unlink archival') {
    Snackbar.error("input doesn't match")
    return
  }
  try {
    await hs.things.deleteHydroShareArchive(props.thingId)
    Snackbar.info('Your site has been unlinked')
    emit('delete')
    emit('close')
  } catch (error) {
    console.error('Error unlinking site', error)
  }
}

function cancelDeletion() {
  deleteInput.value = ''
  emit('close')
}
</script>
