<template>
  <v-card>
    <v-toolbar flat color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" /> Confirm task deletion
      </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-card-text> This action will permanently delete the task: </v-card-text>
    <v-card-text class="py-0">
      <span class="opacity-80">{{ task.name }}</span>
    </v-card-text>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-delete color="delete" @click="onDelete">Delete</v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { TaskExpanded } from '@hydroserver/client'
import { mdiAlert } from '@mdi/js'

const emit = defineEmits(['delete', 'close'])
const props = defineProps({
  task: {
    type: Object as () => TaskExpanded,
    required: true,
  },
})

const onDelete = () => {
  emit('delete', props.task.id)
  emit('close')
}
</script>
