<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-alert
      v-if="showErrors && noMappingsError"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-3"
    >
      At least one source target mapping is required.
    </v-alert>
    <div class="etl-mappings">
      <div class="etl-mappings-head">Source field</div>
      <div class="etl-mappings-head etl-mappings-head-target">
        Target datastream
      </div>

      <template v-for="(m, mi) in task.mappings as any[]" :key="mi">
        <div class="etl-mapping-row">
          <div class="etl-mapping-source">
            <v-text-field
              v-model="m.sourceIdentifier"
              placeholder="CSV column or JSON key"
              density="compact"
              variant="outlined"
              rounded="lg"
              hide-details="auto"
              :rules="rules.requiredAndMaxLength150"
            />
          </div>

          <div class="etl-mapping-arrow">
            <v-icon :icon="mdiArrowRight" size="22" />
          </div>

          <div class="etl-mapping-target">
            <v-btn
              v-if="!ensureSinglePath(m).targetIdentifier"
              variant="outlined"
              rounded="lg"
              type="button"
              class="etl-target-btn text-none"
              :class="{ 'etl-target-btn-error': hasTargetError(mi, 0) }"
              @click="openTargetSelector(mi, 0)"
            >
              <span class="etl-target-btn-label">
                <v-icon :icon="mdiPlusCircleOutline" size="18" />
                <span>Select target datastream</span>
              </span>
            </v-btn>

            <v-btn
              v-else
              variant="outlined"
              rounded="lg"
              type="button"
              class="etl-target-btn etl-target-btn-selected text-none"
              @click="openTargetSelector(mi, 0)"
            >
              <span class="target-selector-content">
                <span class="target-name">
                  {{ datastreamNameById(ensureSinglePath(m).targetIdentifier) }}
                </span>
                <span
                  v-if="
                    datastreamThingNameById(
                      ensureSinglePath(m).targetIdentifier
                    )
                  "
                  class="target-thing"
                >
                  {{
                    datastreamThingNameById(
                      ensureSinglePath(m).targetIdentifier
                    )
                  }}
                </span>
                <span class="target-id">{{
                  String(ensureSinglePath(m).targetIdentifier)
                }}</span>
              </span>
            </v-btn>

            <div
              v-if="hasTargetError(mi, 0)"
              class="text-error text-caption mt-1"
            >
              Target is required
            </div>
          </div>

          <div class="etl-mapping-delete">
            <v-btn
              icon
              variant="text"
              color="red-lighten-1"
              type="button"
              :title="`Delete mapping`"
              @click.stop="removeMapping(mi)"
            >
              <v-icon :icon="mdiTrashCanOutline" size="22" />
            </v-btn>
          </div>
        </div>
      </template>

      <div class="etl-mapping-actions">
        <v-btn
          variant="outlined"
          rounded="lg"
          type="button"
          class="text-none etl-add-mapping-btn"
          :prepend-icon="mdiPlus"
          @click="onAddMapping"
        >
          Add mapping
        </v-btn>
      </div>
    </div>
  </v-form>

  <v-dialog v-model="datastreamSelectorOpen" width="75rem">
    <DatastreamSelectorCard
      card-title="Select a target datastream"
      @selected-datastream="onTargetSelected"
      @close="datastreamSelectorOpen = false"
      enforce-unique-selections
      :draft-datastreams="draftDatastreams"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import type { Mapping, Task } from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'
import { storeToRefs } from 'pinia'
import { DatastreamExtended } from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import {
  mdiArrowRight,
  mdiPlus,
  mdiPlusCircleOutline,
  mdiTrashCanOutline,
} from '@mdi/js'
import { useOrchestrationStore } from '@/store/orchestration'

const task = defineModel<Task>('task', { required: true })
const props = defineProps<{
  workspaceId?: string | null
}>()
const orchestrationStore = useOrchestrationStore()
const {
  linkedDatastreamIds,
  linkedDatastreams,
  draftDatastreams,
  workspaceDatastreams,
  workspaceThings,
} = storeToRefs(orchestrationStore)
const { ensureWorkspaceDatastreams, ensureWorkspaceThings } = orchestrationStore
const resolvedWorkspaceId = computed(() => {
  return (
    props.workspaceId ||
    (task.value as any)?.workspaceId ||
    (task.value as any)?.workspace?.id ||
    null
  )
})

const localForm = ref<VForm>()
const isValid = ref(true)
const showErrors = ref(false)
const missingTargetKeys = ref<Set<string>>(new Set())
const noMappingsError = ref(false)

function hasTargetError(mi: number, pi: number) {
  return showErrors.value && missingTargetKeys.value.has(`${mi}:${pi}`)
}

function ensureSinglePath(mapping: Mapping) {
  const targetDatastreamId = (mapping as any).targetDatastream?.id
  if (!Array.isArray(mapping.paths) || mapping.paths.length === 0) {
    mapping.paths = [
      {
        targetIdentifier: targetDatastreamId ? String(targetDatastreamId) : '',
        dataTransformations: [],
      },
    ]
  }
  if (mapping.paths.length > 1) mapping.paths = [mapping.paths[0]]
  if (!mapping.paths[0].targetIdentifier && targetDatastreamId) {
    mapping.paths[0].targetIdentifier = String(targetDatastreamId)
  }
  if (!Array.isArray(mapping.paths[0].dataTransformations)) {
    mapping.paths[0].dataTransformations = []
  }
  return mapping.paths[0]
}

function enforceMappingShape() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }
  task.value.mappings.forEach((mapping: any) => {
    ensureSinglePath(mapping)
  })
}

function ensureInitialTaskMappings() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }

  if (task.value.mappings.length === 0) {
    task.value.mappings.push(createEmptyMapping())
  }
}

async function validate() {
  const vuetify = await localForm.value?.validate()
  let ok = (vuetify?.valid ?? isValid.value) === true

  showErrors.value = true
  noMappingsError.value = task.value.mappings.length === 0
  if (noMappingsError.value) ok = false

  const nextMissingKeys = new Set<string>()

  task.value.mappings.forEach((m: any, mi) => {
    const path = ensureSinglePath(m)
    if (!path.targetIdentifier) {
      ok = false
      nextMissingKeys.add(`${mi}:0`)
    }
  })

  missingTargetKeys.value = nextMissingKeys
  return ok
}

defineExpose({ validate })

const datastreamSelectorOpen = ref(false)
const activeMi = ref<number | null>(null)
const activePi = ref<number | null>(null)

function datastreamNameById(id: string | number | undefined | null) {
  return datastreamById(id)?.name || ''
}

function datastreamById(id: string | number | undefined | null): any {
  if (id === undefined || id === null || `${id}` === '') return ''
  const key = String(id)
  return (
    workspaceDatastreams.value.find((d) => String(d.id) === key) ||
    linkedDatastreams.value.find((d) => String(d.id) === key) ||
    draftDatastreams.value.find((d) => String(d.id) === key) ||
    task.value.mappings
      ?.map((mapping: any) => mapping?.targetDatastream)
      .find((d: any) => d && String(d.id) === key) ||
    null
  )
}

function datastreamThingNameById(id: string | number | undefined | null) {
  const ds = datastreamById(id)
  if (!ds) return ''
  if (ds.thing?.name) return ds.thing.name
  const thingId = ds.thingId ?? ds.thing_id ?? ds.thing?.id
  if (!thingId) return ''
  return (
    workspaceThings.value.find((thing) => String(thing.id) === String(thingId))
      ?.name || ''
  )
}

function openTargetSelector(mi: number, pi: number) {
  activeMi.value = mi
  activePi.value = pi
  datastreamSelectorOpen.value = true
}

function referencedTargetIds(): Set<string> {
  const ids = new Set<string>()
  for (const m of task.value.mappings as any[]) {
    for (const p of (m as any).paths) {
      const id = p.targetIdentifier
      if (id !== undefined && id !== null && String(id) !== '') {
        ids.add(String(id))
      }
    }
  }
  return ids
}

function syncDraftDatastreams() {
  const refIds = referencedTargetIds()
  const keepIds = new Set(
    [...refIds].filter((id) => !linkedDatastreamIds.value.has(id))
  )

  const byId = new Map<string, DatastreamExtended>()
  for (const ds of draftDatastreams.value) {
    const key = String(ds.id)
    if (keepIds.has(key) && !byId.has(key)) byId.set(key, ds)
  }

  draftDatastreams.value = [...byId.values()]
}

function onTargetSelected(event: DatastreamExtended) {
  const mi = activeMi.value,
    pi = activePi.value
  if (mi == null || pi == null) return
  const m = task.value.mappings[mi] as any
  const p = m?.paths?.[pi]

  p.targetIdentifier = event.id
  draftDatastreams.value = [event, ...draftDatastreams.value]
  syncDraftDatastreams()

  // remove only this row’s error
  const key = `${mi}:${pi}`
  if (missingTargetKeys.value.has(key)) {
    const next = new Set(missingTargetKeys.value)
    next.delete(key)
    missingTargetKeys.value = next
  }

  activeMi.value = activePi.value = null
}

function removeMapping(mi: number) {
  const mappings = task.value.mappings
  if (!Array.isArray(mappings) || mi < 0 || mi >= mappings.length) return
  mappings.splice(mi, 1)
  syncDraftDatastreams()
}

function createEmptyMapping() {
  const mapping = {
    sourceIdentifier: '',
    paths: [
      {
        targetIdentifier: '',
        dataTransformations: [],
      },
    ],
  } as any

  return mapping
}

function onAddMapping() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }
  task.value.mappings.push(createEmptyMapping())
  noMappingsError.value = false
}

watch(
  () => task.value,
  () => {
    ensureInitialTaskMappings()
  },
  { immediate: true }
)

watch(
  resolvedWorkspaceId,
  async (workspaceId) => {
    if (!workspaceId) return
    try {
      await Promise.all([
        ensureWorkspaceDatastreams(workspaceId),
        ensureWorkspaceThings(workspaceId),
      ])
    } catch (error) {
      console.error('Error fetching workspace datastreams and things', error)
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.etl-mappings {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.etl-mappings-head {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  font-size: 0.68rem;
}
.etl-mappings-head-target {
  margin-left: calc((100% - 101px) / 3 + 52px);
}
.etl-mapping-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px minmax(0, 2fr) 44px;
  gap: 5px;
  align-items: center;
}
.etl-mapping-source,
.etl-mapping-target {
  min-width: 0;
  align-self: center;
}
.etl-mapping-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0b8c9;
  min-height: 40px;
}
.etl-mapping-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
}
.etl-target-btn {
  width: 100%;
  min-height: 40px;
  height: auto;
  justify-content: flex-start;
  text-align: left;
  border-style: dashed;
  border-width: 2px;
  border-color: #1565c0;
  color: #1565c0;
  background: #fdfdff;
  font-size: 0.84rem;
  padding-inline: 12px;
  padding-block: 6px;
}
.etl-target-btn-error {
  border-color: #d32f2f;
  color: #d32f2f;
}
.etl-target-btn-selected {
  border-style: solid;
  background: #f6f9ff;
  color: #1c1b1f;
  min-height: 62px;
}
.etl-target-btn-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
}
.etl-target-btn :deep(.v-btn__content) {
  justify-content: flex-start;
  text-align: left;
  width: 100%;
  min-width: 0;
  overflow: visible;
}
.etl-mapping-actions {
  margin-top: 1px;
}
.etl-add-mapping-btn {
  min-height: 38px;
  border-width: 2px;
  border-color: #1565c0;
  color: #1565c0;
  font-size: 0.84rem;
  border-style: dashed;
}

:deep(.etl-mapping-source .v-field) {
  --v-input-control-height: 38px;
}

:deep(.etl-mapping-source .v-field__input) {
  min-height: 38px;
  padding-top: 0;
  padding-bottom: 0;
  font-size: 0.86rem;
  text-align: left;
}

.swimlanes {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  column-gap: 12px;
  row-gap: 8px;
  margin-bottom: 12px;
}
.swimlanes-aggregation {
  --aggregation-statistic-width: 18rem;
  grid-template-columns:
    minmax(0, 1fr)
    fit-content(var(--aggregation-statistic-width))
    minmax(0, 2fr);
  column-gap: 12px;
}
.head {
  font-weight: 600;
  color: rgba(0, 0, 0, 0.6);
  padding-bottom: 6px;
}
.cell {
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  padding: 6px 8px;
  min-height: 34px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
.aggregation-plain-cell {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
  min-height: 0;
}
.source {
  background: transparent;
  border: none;
  padding-left: 0;
}
.source-empty {
  min-height: 0;
}
.mapping-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  grid-column: 1 / -1; /* make the action row span all 3 columns */
  margin-top: 4px;
}

.target-selector-btn {
  max-width: calc(100% - 2.25rem);
  height: auto;
  transition:
    transform 0.14s ease,
    box-shadow 0.14s ease,
    background-color 0.14s ease;
}

.swimlanes-aggregation .target-selector-btn {
  margin-right: 0 !important;
  max-width: 100%;
  width: 100%;
}

.swimlanes-aggregation .aggregation-statistic-select,
.swimlanes-aggregation .aggregation-statistic-error {
  max-width: var(--aggregation-statistic-width);
  width: var(--aggregation-statistic-width);
}

.target-selector-btn :deep(.v-btn__content) {
  display: flex;
  justify-content: flex-start;
  text-align: left;
  white-space: normal;
  width: 100%;
}

.target-selector-btn:hover,
.target-selector-btn:focus-visible {
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
  transform: translateY(-1px);
}

.target-selector-btn-selected {
  justify-content: flex-start;
  min-width: 0;
}

.target-selector-content {
  display: block;
  max-width: 100%;
  line-height: 1.25;
  padding-block: 2px;
}

.target-id {
  display: block;
  color: rgba(0, 0, 0, 0.55);
  font-size: 0.72rem;
  overflow-wrap: anywhere;
  white-space: normal;
}

.target-name {
  color: #1c1b1f;
  display: block;
  font-weight: 600;
  overflow-wrap: anywhere;
  white-space: normal;
}

.target-thing {
  color: rgba(0, 0, 0, 0.66);
  display: block;
  font-size: 0.78rem;
  overflow-wrap: anywhere;
  white-space: normal;
}

.aggregation-field-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
}

.target-selector-btn-error {
  box-shadow: 0 0 0 1px rgba(211, 47, 47, 0.3);
}

.aggregation-field-error {
  display: block;
  width: 100%;
}

@media (max-width: 960px) {
  .etl-mappings-head-target {
    margin-left: 0;
  }

  .etl-mapping-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .etl-mapping-arrow,
  .etl-mapping-delete {
    justify-content: flex-start;
    min-height: 0;
  }
}
</style>
