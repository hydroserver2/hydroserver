<template>
  <v-snackbar
    v-model="snack.visible"
    :timeout="snack.timeout"
    :color="snack.color"
    multi-line
    :location="snack.position"
  >
    <div class="d-flex align-center ga-4 text-white">
      <v-icon
        v-if="snack.icon !== SnackIcon.None"
        :icon="iconMap[snack.icon]"
        color="white"
        size="45"
      />
      <div>
        <h6 class="text-title-large">{{ snack.title }}</h6>
        <div>{{ snack.message }}</div>
      </div>
    </div>
  </v-snackbar>
</template>

<script lang="ts" setup>
import { onBeforeUnmount, ref } from 'vue'
import { Snackbar, Snack, SnackIcon } from '@uwrl/qc-utils'
import {
  mdiCheckboxMarkedCircle,
  mdiAlert,
  mdiAlertCircle,
  mdiInformation,
} from '@mdi/js'

const iconMap: Record<SnackIcon, string> = {
  [SnackIcon.Success]: mdiCheckboxMarkedCircle,
  [SnackIcon.Warning]: mdiAlert,
  [SnackIcon.Error]: mdiAlertCircle,
  [SnackIcon.Info]: mdiInformation,
  [SnackIcon.None]: '',
}

const snack = ref<Snack>(new Snack())

const showSnack = (newSnack: Snack) => (snack.value = { ...newSnack })
let subscription = Snackbar.snack$.subscribe(showSnack)

onBeforeUnmount(() => subscription.unsubscribe())
</script>
