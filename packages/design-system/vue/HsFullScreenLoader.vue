<template>
  <v-container class="fill-height">
    <v-row justify="center" align="center">
      <v-col class="text-center" cols="12">
        <h5 class="hs-text-md">{{ loadingText }}</h5>
      </v-col>
      <v-col cols="6" sm="2">
        <v-progress-linear color="primary" height="8" indeterminate rounded />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
defineOptions({ name: 'HsFullScreenLoader' })

withDefaults(defineProps<{ loadingText?: string }>(), {
  loadingText: 'Loading page…',
})
</script>
