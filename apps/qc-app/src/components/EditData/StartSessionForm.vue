<template>
  <div class="qc-start-session-form pa-4">
    <div class="text-body-1 font-weight-medium mb-3">Start new edit session</div>

    <v-text-field
      v-model="start"
      data-testid="session-start"
      label="Start"
      type="datetime-local"
      density="compact"
      hide-details="auto"
      class="mb-2"
    />
    <v-text-field
      v-model="end"
      data-testid="session-end"
      label="End"
      type="datetime-local"
      density="compact"
      :error-messages="endError"
      hide-details="auto"
      class="mb-2"
    />
    <v-textarea
      v-model="description"
      data-testid="session-description"
      label="Description (optional)"
      rows="2"
      density="compact"
      auto-grow
      hide-details="auto"
      class="mb-3"
    />

    <div class="d-flex justify-end ga-2">
      <v-btn data-testid="session-cancel" variant="text" @click="emit('cancel')">
        Cancel
      </v-btn>
      <v-btn
        data-testid="session-confirm"
        color="primary"
        variant="flat"
        :disabled="!isValid"
        @click="onConfirm"
      >
        Start session
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { QualityControlSessionContract } from '@hydroserver/client'

type QcSessionPostBody = QualityControlSessionContract.PostBody

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'confirm', spec: QcSessionPostBody): void
}>()

const start = ref('')
const end = ref('')
const description = ref('')

const startMs = computed(() => new Date(start.value).getTime())
const endMs = computed(() => new Date(end.value).getTime())

const endError = computed(() =>
  start.value && end.value && endMs.value <= startMs.value
    ? 'End must be after start'
    : ''
)

const isValid = computed(
  () => !!start.value && !!end.value && endMs.value > startMs.value
)

function onConfirm(): void {
  if (!isValid.value) return
  emit('confirm', {
    phenomenonTimeStart: new Date(start.value).toISOString(),
    phenomenonTimeEnd: new Date(end.value).toISOString(),
    description: description.value.trim() || undefined,
  })
}
</script>
