<template>
  <v-chip
    size="small"
    :color="scope === 'workspace' ? 'primary' : undefined"
    variant="tonal"
  >
    {{ scope === 'workspace' ? 'Workspace' : 'System' }}
  </v-chip>
</template>

<script setup lang="ts">
defineProps<{
  scope: 'workspace' | 'system' | undefined
}>()
</script>
