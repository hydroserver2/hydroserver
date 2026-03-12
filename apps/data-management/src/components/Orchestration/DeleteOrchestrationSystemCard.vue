<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" />
        Confirm orchestration system deletion
      </v-card-title>
    </v-toolbar>

    <v-card-text v-if="relatedSources.length > 0">
      <v-alert>
        Before you remove <strong> {{ orchestrationSystem.name }} </strong> as
        an orchestration system, you must delete all of its related tasks.
      </v-alert>
    </v-card-text>

    <v-card-text v-if="orchestrationSystem.type === 'SDL'">
      <v-card
        variant="outlined"
        class="pa-4 rounded-lg"
        color="delete"
        elevation="0"
      >
        <strong>Note:</strong> You'll need to uninstall the Streaming Data
        Loader software from your machine before removing it here, otherwise
        your machine will re-register itself the next time it's scheduled to
        run.
      </v-card>
    </v-card-text>

    <v-card-text>
      Please type the orchestration system name (<strong>{{
        orchestrationSystem?.name
      }}</strong
      >) to confirm deletion:
      <v-form>
        <v-text-field
          class="pt-2"
          v-model="deleteInput"
          label="Orchestration system name"
          solo
          @keydown.enter.prevent="onDelete"
        ></v-text-field>
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-delete color="delete" @click="onDelete" :disabled="!canDelete">
        Delete
      </v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import hs, {
  Task,
  OrchestrationSystem,
  TaskExpanded,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, ref } from 'vue'
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['delete', 'close'])
const props = defineProps({
  orchestrationSystem: {
    type: Object as () => OrchestrationSystem,
    required: true,
  },
  tasks: { type: Object as () => TaskExpanded[], required: true },
})

const deleteInput = ref('')

const relatedSources = computed(() =>
  props.tasks.filter(
    (ds) => ds.orchestrationSystem?.id === props.orchestrationSystem.id
  )
)

const canDelete = computed(
  () =>
    relatedSources.value.length === 0 &&
    deleteInput.value.trim().toLowerCase() ===
      props.orchestrationSystem.name.toLowerCase()
)

const onDelete = async () => {
  if (
    deleteInput.value.toLowerCase() !==
    props.orchestrationSystem.name.toLowerCase()
  ) {
    Snackbar.warn('Name does not match.')
    return
  }
  if (relatedSources.value.length > 0) {
    Snackbar.warn(
      `Before you remove ${props.orchestrationSystem.name} as an orchestration system, you must delete all of its related tasks.`
    )
    return
  }

  const res = await hs.orchestrationSystems.delete(props.orchestrationSystem.id)
  if (res.ok) emit('delete')
  else {
    console.error('Error deleting orchestration system', res)
    Snackbar.error(res.message)
  }
  emit('close')
}
</script>
