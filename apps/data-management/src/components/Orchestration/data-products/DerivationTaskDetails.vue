<template>
  <SimpleProductTaskDetails
    task-label="derivation"
    :task-id="taskId"
    :run-id="runId"
    :embedded="embedded"
    :initial-task="initialTask"
    @close="$emit('close')"
    @deleted="$emit('deleted')"
    @updated="$emit('updated')"
  />
</template>

<script setup lang="ts">
import SimpleProductTaskDetails from './SimpleProductTaskDetails.vue'
defineProps<{ taskId: string; runId?: string | null; embedded?: boolean; initialTask?: any }>()
defineEmits(['close', 'deleted', 'updated'])
</script>
