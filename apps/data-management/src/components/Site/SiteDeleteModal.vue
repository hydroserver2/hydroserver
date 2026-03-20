<template>
  <v-card>
    <v-card-title>
      <span class="text-h5">Confirm Deletion</span>
    </v-card-title>
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
      Please type the site name (<strong>{{ thing?.name }}</strong
      >) to confirm deletion:
      <v-form>
        <v-text-field
          class="pt-2"
          v-model="deleteInput"
          label="Site name"
          solo
          @keydown.enter.prevent="onDeleteThing"
        ></v-text-field>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-delete color="delete" @click="onDeleteThing">Delete</v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Thing } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'

const emit = defineEmits(['switchToAccessControl', 'delete', 'close'])
const props = defineProps({
  thing: {
    type: Object as () => Thing,
    required: true,
  },
})

const deleteInput = ref('')

const onDeleteThing = () => {
  if (deleteInput.value.toLowerCase() !== props.thing.name.toLowerCase()) {
    Snackbar.warn('Site name does not match.')
    return
  }
  emit('delete')
}
</script>
