<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" />
        Confirm orchestration system deletion
      </v-card-title>
    </v-toolbar>

    <v-card-text v-if="hasLinkedTasks">
      <v-alert>
        Before you remove <strong>{{ orchestrationSystem.name }}</strong
        >, you must delete its {{ linkedTaskCount }}
        {{ linkedTaskCount === 1 ? 'linked task' : 'linked tasks' }}
        <template v-if="orchestrationSystem.workspaceId == null">
          across all workspaces
        </template>
        first.
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
import hs, { OrchestrationSystem } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, ref } from 'vue'
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['delete', 'close'])
const props = defineProps({
  orchestrationSystem: {
    type: Object as () => OrchestrationSystem,
    required: true,
  },
})

const deleteInput = ref('')

const linkedTaskCount = computed(() => {
  const count = Number(props.orchestrationSystem.taskCount ?? 0)
  return Number.isFinite(count) && count > 0 ? count : 0
})
const hasLinkedTasks = computed(() => linkedTaskCount.value > 0)

const canDelete = computed(
  () =>
    !hasLinkedTasks.value &&
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
  if (hasLinkedTasks.value) {
    Snackbar.warn(
      `Before you remove ${props.orchestrationSystem.name}, you must delete its linked tasks first.`
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
