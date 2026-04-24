<template>
  <v-card>
    <v-card-title>ExpressionForm</v-card-title>
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Close</v-btn-cancel>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
defineEmits<{
  (e: 'close'): void
}>()
</script>
