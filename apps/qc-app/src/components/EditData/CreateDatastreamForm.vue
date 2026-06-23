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

    <div
      v-if="onCreateProcessingLevel && !permissionError && !showAddLevel"
      class="d-flex align-center ga-2 mb-3"
    >
      <span
        v-if="!processingLevels.length"
        class="text-body-small text-medium-emphasis"
      >
        No processing levels in this workspace yet.
      </span>
      <v-spacer />
      <v-btn
        data-testid="add-level-toggle"
        size="small"
        variant="text"
        color="primary"
        prepend-icon="mdi-plus"
        @click="showAddLevel = true"
      >
        Add processing level
      </v-btn>
    </div>

    <v-expand-transition>
      <div v-if="showAddLevel" class="qc-add-level rounded border pa-3 mb-3">
        <div class="text-body-small font-weight-medium mb-2">
          New processing level
        </div>
        <v-text-field
          v-model="newLevel.code"
          data-testid="new-level-code"
          label="Code *"
          density="compact"
          hide-details="auto"
          class="mb-2"
        />
        <v-text-field
          v-model="newLevel.definition"
          data-testid="new-level-definition"
          label="Definition"
          density="compact"
          hide-details="auto"
          class="mb-2"
        />
        <v-textarea
          v-model="newLevel.explanation"
          data-testid="new-level-explanation"
          label="Explanation"
          rows="2"
          auto-grow
          density="compact"
          hide-details="auto"
          class="mb-3"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn
            data-testid="new-level-cancel"
            size="small"
            variant="text"
            :disabled="addingLevel"
            @click="cancelAddLevel"
          >
            Cancel
          </v-btn>
          <v-btn
            data-testid="new-level-save"
            size="small"
            color="primary"
            variant="flat"
            :disabled="!newLevel.code.trim()"
            :loading="addingLevel"
            @click="onAddLevel"
          >
            Add
          </v-btn>
        </div>
      </div>
    </v-expand-transition>

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
  /** Creates a processing level in the active workspace and resolves with the
   *  new level (or null on failure). When provided, an inline "Add processing
   *  level" affordance is shown so users don't have to leave for the
   *  management app. The parent is expected to add the result to
   *  `processingLevels`. */
  onCreateProcessingLevel?: (input: {
    code: string
    definition?: string
    explanation?: string
  }) => Promise<{ id: string } | null>
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'confirm', spec: CreateDatastreamSpec): void
}>()

const knownLevelIds = computed(
  () => new Set(props.processingLevels.map((p) => p.id))
)

// Only honour a remembered default if it exists in THIS workspace's
// processing levels. A level id persisted against another workspace or
// backend would otherwise be submitted and rejected ("Processing level
// does not exist").
const processingLevelId = ref<string | null>(
  props.defaultProcessingLevelId &&
    knownLevelIds.value.has(props.defaultProcessingLevelId)
    ? props.defaultProcessingLevelId
    : null
)
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
    knownLevelIds.value.has(processingLevelId.value) &&
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

// --- Inline "add processing level" -------------------------------------
const showAddLevel = ref(false)
const addingLevel = ref(false)
const newLevel = ref({ code: '', definition: '', explanation: '' })

function cancelAddLevel(): void {
  showAddLevel.value = false
  newLevel.value = { code: '', definition: '', explanation: '' }
}

async function onAddLevel(): Promise<void> {
  const code = newLevel.value.code.trim()
  if (!code || !props.onCreateProcessingLevel) return
  addingLevel.value = true
  try {
    const created = await props.onCreateProcessingLevel({
      code,
      definition: newLevel.value.definition.trim() || undefined,
      explanation: newLevel.value.explanation.trim() || undefined,
    })
    // Parent appends the new level to `processingLevels`, so selecting its id
    // here lands on a now-valid option.
    if (created) {
      processingLevelId.value = created.id
      cancelAddLevel()
    }
  } finally {
    addingLevel.value = false
  }
}
</script>
