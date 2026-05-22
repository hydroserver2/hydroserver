<template>
  <v-snackbar
    v-model="snack.visible"
    :timeout="snack.timeout"
    :color="snack.color"
    multi-line
    :location="snack.position"
  >
    <div class="d-flex align-center ga-4 text-white">
      <v-icon color="white" size="45">{{ snack.icon }}</v-icon>
      <div>
        <h6 class="text-title-large">{{ snack.title }}</h6>
        <div>{{ snack.message }}</div>
      </div>
    </div>
  </v-snackbar>
</template>

<script lang="ts" setup>
import { onBeforeUnmount, ref } from 'vue'
import { Snackbar, Snack } from '@uwrl/qc-utils'

const snack = ref<Snack>(new Snack())

const showSnack = (newSnack: Snack) => (snack.value = { ...newSnack })
let subscription = Snackbar.snack$.subscribe(showSnack)

onBeforeUnmount(() => subscription.unsubscribe())
</script>
