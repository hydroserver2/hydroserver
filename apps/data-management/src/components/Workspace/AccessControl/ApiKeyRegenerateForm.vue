<template>
  <v-card>
    <v-toolbar flat color="yellow-darken-4">
      <v-card-title class="text-h5">
        Confirm API key regeneration
      </v-card-title>
    </v-toolbar>

    <v-card-text>
      This action will replace the existing api key with a new one.
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary color="yellow-darken-4" @click="onDelete">
        Regenerate key
      </v-btn-primary>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
const emit = defineEmits(['regenerated', 'close'])

const onDelete = () => {
  emit('regenerated')
  emit('close')
}
</script>
