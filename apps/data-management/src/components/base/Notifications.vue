<template>
  <v-snackbar
    v-model="snack.visible"
    :timeout="snack.timeout"
    :color="snack.color"
    multi-line
    :location="snack.position"
  >
    <v-row align="center">
      <v-col cols="auto">
        <v-icon
          v-if="snack.icon"
          :icon="iconMap[snack.icon]"
          dark
          color="white"
          size="45"
        />
      </v-col>
      <v-col>
        <div class="text-white">
          <h6 class="text-h6">{{ snack.title }}</h6>
          <div>{{ snack.message }}</div>
        </div>
      </v-col>
    </v-row>
  </v-snackbar>
</template>

<script lang="ts" setup>
import { onBeforeUnmount, ref } from 'vue'
import { Snackbar, Snack } from '@/utils/notifications'
import {
  mdiCheckboxMarkedCircle,
  mdiAlert,
  mdiAlertCircle,
  mdiInformation,
} from '@mdi/js'

const iconMap: Record<string, string> = {
  'mdi-checkbox-marked-circle': mdiCheckboxMarkedCircle,
  'mdi-alert': mdiAlert,
  'mdi-alert-circle': mdiAlertCircle,
  'mdi-information': mdiInformation,
  none: '',
}

const snack = ref<Snack>(new Snack())

const showSnack = (newSnack: Snack) => (snack.value = { ...newSnack })
let subscription = Snackbar.snack$.subscribe(showSnack)

onBeforeUnmount(() => subscription.unsubscribe())
</script>
