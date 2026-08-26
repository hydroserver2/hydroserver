<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="hs-text-md">
        <v-icon :icon="mdiAlert" /> Confirm Deletion
      </v-card-title>
    </v-toolbar>
    <v-card-text>
      This action will permanently delete the site along with all associated
      datastreams and observations
      <strong>for all users of this system</strong>. If you want to keep your
      data, you can backup to HydroShare or download a local copy before
      deletion. Alternatively, you can pass ownership of this site to someone
      else using the
      <v-btn class="px-0" variant="text" @click="emit('switchToAccessControl')"
        >Access Control</v-btn
      >
      dialog.
    </v-card-text>
    <v-card-text>
      Please type the site name (<strong>{{ monitoringSite?.name }}</strong
      >) to confirm deletion:
      <v-form>
        <v-text-field
          class="pt-2"
          v-model="deleteInput"
          label="Site name"
          solo
          @keydown.enter.prevent="onDeleteMonitoringSite"
        ></v-text-field>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-destructive @click="onDeleteMonitoringSite">Delete</v-btn-destructive>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { MonitoringSite } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['switchToAccessControl', 'delete', 'close'])
const props = defineProps({
  monitoringSite: {
    type: Object as () => MonitoringSite,
    required: true,
  },
})

const deleteInput = ref('')

const onDeleteMonitoringSite = () => {
  if (deleteInput.value.toLowerCase() !== props.monitoringSite.name.toLowerCase()) {
    Snackbar.warn('Site name does not match.')
    return
  }
  emit('delete')
}
</script>
