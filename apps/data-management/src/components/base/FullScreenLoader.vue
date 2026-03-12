<template>
  <v-container class="fill-height">
    <v-row justify="center" align="center">
      <v-col class="text-center" cols="12">
        <h5 class="text-h5">{{ loadingText }}</h5>
      </v-col>
      <v-col cols="6" sm="2">
        <v-progress-linear
          color="blue-accent-4"
          height="8"
          indeterminate
          rounded
        ></v-progress-linear>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
const props = defineProps({
  loadingText: { type: String, default: 'Loading page...' },
})
</script>
