<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" /> Confirm workspace deletion
      </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-card-text>
      This action will permanently delete the workspace along with all sites,
      datastreams, metadata, and user permissions associated with this
      workspace. If you want to keep your data, you can backup to HydroShare or
      download a local copy before deletion. Alternatively, you can pass
      ownership of this workspace to someone else using the
      <v-btn class="px-0" variant="text" @click="emit('switchToAccessControl')"
        >Access Control</v-btn
      >
      dialog.
    </v-card-text>
    <v-card-text>
      Please type the workspace name (<strong>{{ workspace?.name }}</strong
      >) to confirm deletion:
      <v-form>
        <v-text-field
          class="pt-2"
          v-model="deleteInput"
          label="Workspace name"
          solo
          @keydown.enter.prevent="onDelete"
        ></v-text-field>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-delete color="delete" @click="onDelete">Delete</v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { Workspace } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { ref } from 'vue'
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['switchToAccessControl', 'delete', 'close'])
const props = defineProps({
  workspace: {
    type: Object as () => Workspace,
    required: true,
  },
})

const deleteInput = ref('')

const onDelete = () => {
  if (deleteInput.value.toLowerCase() !== props.workspace.name.toLowerCase()) {
    Snackbar.warn('Workspace name does not match.')
    return
  }
  emit('delete')
  emit('close')
}
</script>
