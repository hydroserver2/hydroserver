<template>
  <div class="qc-create-datastream-form pa-4">
    <div class="text-body-1 font-weight-medium mb-1">
      Set up QC editing for "{{ source.name }}"
    </div>
    <div class="text-body-small text-medium-emphasis mb-3">
      Creates an empty managed datastream from this source, links a QC history,
      and tags the source.
    </div>

    <v-alert
      v-if="permissionError"
      data-testid="create-permission-error"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-3"
      :text="permissionError"
    />

    <v-select
      v-model="processingLevelId"
      data-testid="create-processing-level"
      :items="processingLevelItems"
      item-title="title"
      item-value="value"
      label="New processing level"
      density="compact"
      :error-messages="processingLevelError"
      hide-details="auto"
      class="mb-2"
    />
    <v-text-field
      v-model="name"
      data-testid="create-name"
      label="Name"
      density="compact"
      hide-details="auto"
      class="mb-3"
    />

    <div class="d-flex justify-end ga-2">
      <v-btn data-testid="create-cancel" variant="text" @click="emit('cancel')">
        Cancel
      </v-btn>
      <v-btn
        data-testid="create-confirm"
        color="primary"
        variant="flat"
        :disabled="!isValid"
        @click="onConfirm"
      >
        Create datastream
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Datastream } from '@hydroserver/client'

interface ProcessingLevelOption {
  id: string
  definition?: string
  code?: string
}

export interface CreateDatastreamSpec {
  source: Datastream
  processingLevelId: string
  name?: string
}

const props = defineProps<{
  source: Datastream
  processingLevels: ProcessingLevelOption[]
  defaultProcessingLevelId?: string | null
  /** When set, the user can't create datastreams here: shown as a warning
   *  and the confirm button is disabled. */
  permissionError?: string
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'confirm', spec: CreateDatastreamSpec): void
}>()

const processingLevelId = ref<string | null>(props.defaultProcessingLevelId ?? null)
const name = ref(`${props.source.name} (QC)`)

const processingLevelItems = computed(() =>
  props.processingLevels.map((p) => ({
    title: p.definition || p.code || p.id,
    value: p.id,
  }))
)

// The managed datastream must use a different processing level than the
// source. Datastreams load expand_related (nested processingLevel), so read
// the id from either shape.
const sourceProcessingLevelId = computed(() => {
  const s = props.source as Datastream & { processingLevel?: { id: string } }
  return s.processingLevelId ?? s.processingLevel?.id ?? null
})
const processingLevelError = computed(() =>
  processingLevelId.value &&
  processingLevelId.value === sourceProcessingLevelId.value
    ? 'Must differ from the source processing level'
    : ''
)

const isValid = computed(
  () =>
    !!processingLevelId.value &&
    !processingLevelError.value &&
    !props.permissionError
)

function onConfirm(): void {
  if (!isValid.value || !processingLevelId.value) return
  emit('confirm', {
    source: props.source,
    processingLevelId: processingLevelId.value,
    name: name.value.trim() || undefined,
  })
}
</script>
