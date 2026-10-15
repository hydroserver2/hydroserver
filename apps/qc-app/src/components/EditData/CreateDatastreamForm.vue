<template>
  <div class="qc-create-datastream-form pa-4">
    <div class="text-title-medium font-weight-bold mb-1">
      Set up QC editing for "{{ source.name }}"
    </div>
    <div class="text-body-small text-medium-emphasis mb-3">
      Creates an empty managed datastream from this source and links a QC
      history to it.
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
          v-model="newLevel.name"
          data-testid="new-level-name"
          label="Name *"
          density="compact"
          hide-details="auto"
          class="mb-2"
        />
        <v-text-field
          v-model="newLevel.code"
          data-testid="new-level-code"
          label="Code"
          density="compact"
          hide-details="auto"
          class="mb-2"
        />
        <v-textarea
          v-model="newLevel.description"
          data-testid="new-level-description"
          label="Description *"
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
            :disabled="!newLevel.name.trim() || !newLevel.description.trim()"
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
      class="mb-2"
    />

    <v-textarea
      v-model="description"
      data-testid="create-description"
      label="Description"
      rows="2"
      auto-grow
      density="compact"
      :error-messages="descriptionError"
      hide-details="auto"
      class="mb-2"
    />

    <v-select
      v-model="status"
      data-testid="create-status"
      :items="statusItems"
      label="Status"
      density="compact"
      clearable
      hide-details="auto"
      class="mb-2"
    />

    <v-select
      v-model="methodId"
      data-testid="create-method"
      :items="methodItems"
      item-title="title"
      item-value="value"
      label="Select method"
      no-data-text="No available methods"
      density="compact"
      :error-messages="methodError"
      hide-details="auto"
      class="mb-3"
    />

    <div class="d-flex justify-end ga-2">
      <v-btn
        data-testid="create-cancel"
        variant="text"
        :disabled="loading"
        @click="emit('cancel')"
      >
        Cancel
      </v-btn>
      <v-btn
        data-testid="create-confirm"
        color="primary"
        variant="flat"
        :disabled="!isValid"
        :loading="loading"
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
import type { CreateManagedDatastreamSpec } from '@/composables/useCreateManagedDatastream'
import type { NewProcessingLevelInput } from '@/composables/useProcessingLevels'

interface ProcessingLevelOption {
  id: string
  name?: string
  code?: string | null
}

interface MethodOption {
  id: string
  name: string
}

const props = defineProps<{
  source: Datastream
  processingLevels: ProcessingLevelOption[]
  /** The workspace's methods. Empty when the list could not be loaded, and
   *  the source's own method is then the only option. */
  methods?: MethodOption[]
  /** The datastream status vocabulary. Empty when it could not be loaded. */
  statuses?: string[]
  defaultProcessingLevelId?: string | null
  /** When set, the user can't create datastreams here: shown as a warning
   *  and the confirm button is disabled. */
  permissionError?: string
  /** True while the datastream is being created. */
  loading?: boolean
  /** Creates a processing level in the active workspace and resolves with the
   *  new level (or null on failure). When provided, an inline "Add processing
   *  level" affordance is shown so users don't have to leave for the
   *  management app. The parent is expected to add the result to
   *  `processingLevels`. */
  onCreateProcessingLevel?: (
    input: NewProcessingLevelInput
  ) => Promise<{ id: string } | null>
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'confirm', spec: CreateManagedDatastreamSpec): void
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
const description = ref(props.source.description ?? '')
const status = ref<string | null>(props.source.status ?? null)

// Datastreams load expand_related, so the method arrives nested.
const sourceMethod = computed(() => {
  const s = props.source as Datastream & { method?: MethodOption }
  return { id: props.source.methodId ?? s.method?.id ?? '', name: s.method?.name }
})
const methodId = ref(sourceMethod.value.id)

// The source's own value stays selectable when the list is missing it, so a
// failed load never silently changes what gets created.
const statusItems = computed(() => {
  const items = [...(props.statuses ?? [])]
  const current = props.source.status
  if (current && !items.includes(current)) items.unshift(current)
  return items
})

const methodItems = computed(() => {
  const items = (props.methods ?? []).map((s) => ({
    title: s.name,
    value: s.id,
  }))
  const { id, name: methodName } = sourceMethod.value
  if (id && !items.some((i) => i.value === id)) {
    items.unshift({ title: methodName || "The source's method", value: id })
  }
  return items
})

const descriptionError = computed(() =>
  description.value.trim() ? '' : 'A description is required'
)

const methodError = computed(() => (methodId.value ? '' : 'A method is required'))

const processingLevelItems = computed(() =>
  props.processingLevels.map((p) => ({
    title: p.name || p.code || p.id,
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
    !descriptionError.value &&
    !!methodId.value &&
    !props.permissionError
)

function onConfirm(): void {
  if (props.loading || !isValid.value || !processingLevelId.value) return
  emit('confirm', {
    source: props.source,
    processingLevelId: processingLevelId.value,
    name: name.value.trim() || undefined,
    description: description.value.trim(),
    status: status.value || undefined,
    methodId: methodId.value,
  })
}

// --- Inline "add processing level" -------------------------------------
const showAddLevel = ref(false)
const addingLevel = ref(false)
const newLevel = ref({ name: '', code: '', description: '' })

function cancelAddLevel(): void {
  showAddLevel.value = false
  newLevel.value = { name: '', code: '', description: '' }
}

async function onAddLevel(): Promise<void> {
  const name = newLevel.value.name.trim()
  const description = newLevel.value.description.trim()
  if (!name || !description || !props.onCreateProcessingLevel) return
  addingLevel.value = true
  try {
    const created = await props.onCreateProcessingLevel({
      name,
      description,
      code: newLevel.value.code.trim() || undefined,
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
