<template>
  <SimpleProductTaskDetails
    task-label="rating curve"
    :task-id="taskId"
    :run-id="runId"
    :embedded="embedded"
    @close="$emit('close')"
    @deleted="$emit('deleted')"
    @updated="$emit('updated')"
  />
</template>

<script setup lang="ts">
import SimpleProductTaskDetails from './SimpleProductTaskDetails.vue'
defineProps<{ taskId: string; runId?: string | null; embedded?: boolean }>()
defineEmits(['close', 'deleted', 'updated'])
</script>
