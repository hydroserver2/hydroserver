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
    <template v-if="!isAggregationTask">
      <div class="etl-mappings">
        <div class="etl-mappings-head">Source field</div>
        <div class="etl-mappings-head etl-mappings-head-target">
          Target datastream
        </div>

        <template v-for="(m, mi) in (task.mappings as any[])" :key="mi">
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
                height="40"
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
                height="40"
                type="button"
                class="etl-target-btn etl-target-btn-selected text-none"
                @click="openTargetSelector(mi, 0)"
              >
                <span class="target-selector-content">
                  <span class="target-id">{{
                    String(ensureSinglePath(m).targetIdentifier)
                  }}</span>
                  <span class="target-name">
                    {{
                      datastreamNameById(ensureSinglePath(m).targetIdentifier)
                    }}
                  </span>
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
    </template>

    <template v-else>
      <div
        :class="['swimlanes', { 'swimlanes-aggregation': isAggregationTask }]"
      >
        <div class="head">Source datastream</div>
        <div class="head">Aggregation statistic</div>
        <div class="head">Target datastream</div>

        <template v-for="(m, mi) in (task.mappings as any[])" :key="mi">
          <template v-for="(p, pi) in ((m as any).paths as any[])" :key="pi">
            <div class="cell">
              <template v-if="pi === 0" class="d-flex align-center w-100">
                <v-btn
                  v-if="!m.sourceIdentifier"
                  size="small"
                  variant="outlined"
                  type="button"
                  :color="
                    aggregationSourceMissing ? 'error' : 'green-lighten-1'
                  "
                  class="mr-4 target-selector-btn text-none"
                  :class="{
                    'target-selector-btn-error': aggregationSourceMissing,
                  }"
                  @click="openAggregationDatastreamSelector('source', mi, pi)"
                  :prepend-icon="mdiImport"
                >
                  Select source datastream
                </v-btn>

                <v-btn
                  v-else
                  size="small"
                  variant="tonal"
                  color="green-darken-2"
                  type="button"
                  class="mr-4 target-selector-btn target-selector-btn-selected text-none"
                  :prepend-icon="mdiImport"
                  @click="openAggregationDatastreamSelector('source', mi, pi)"
                >
                  <span class="target-selector-content">
                    <span class="target-id">{{
                      String(m.sourceIdentifier)
                    }}</span>
                    <span class="target-name">
                      {{ datastreamNameById(m.sourceIdentifier) }}
                    </span>
                  </span>
                </v-btn>

                <div
                  v-if="aggregationSourceMissing"
                  class="text-error text-caption mt-1"
                >
                  Source datastream is required
                </div>
              </template>
            </div>

            <div :class="['cell', 'aggregation-plain-cell']">
              <v-select
                class="aggregation-statistic-select"
                :model-value="getAggregationStatistic(p)"
                :items="aggregationStatisticOptions"
                item-title="title"
                item-value="value"
                label="Aggregation statistic *"
                density="compact"
                :rules="rules.required"
                @update:model-value="setAggregationStatistic(p, $event)"
              />
              <div
                v-if="aggregationStatisticMissing"
                class="text-error text-caption mt-1 aggregation-statistic-error"
              >
                Aggregation statistic is required
              </div>
            </div>

            <div :class="['cell', 'd-flex', 'align-center', 'w-100']">
              <div class="aggregation-field-stack">
                <v-btn
                  v-if="!p.targetIdentifier"
                  size="small"
                  variant="outlined"
                  type="button"
                  :color="
                    aggregationTargetMissing ? 'error' : 'green-lighten-1'
                  "
                  class="mr-4 target-selector-btn text-none"
                  :class="{
                    'target-selector-btn-error': aggregationTargetMissing,
                  }"
                  @click="openAggregationDatastreamSelector('target', mi, pi)"
                  :prepend-icon="mdiImport"
                >
                  Select target datastream
                </v-btn>

                <v-btn
                  v-else
                  size="small"
                  variant="tonal"
                  color="green-darken-2"
                  type="button"
                  class="mr-4 target-selector-btn target-selector-btn-selected text-none"
                  :prepend-icon="mdiImport"
                  @click="openAggregationDatastreamSelector('target', mi, pi)"
                >
                  <span class="target-selector-content">
                    <span class="target-id">{{
                      String(p.targetIdentifier)
                    }}</span>
                    <span class="target-name">
                      {{ datastreamNameById(p.targetIdentifier) }}
                    </span>
                  </span>
                </v-btn>

                <div
                  v-if="aggregationTargetMissing"
                  class="text-error text-caption mt-1 aggregation-field-error"
                >
                  Target datastream is required
                </div>
              </div>
            </div>
          </template>

          <div class="mapping-actions">
            <v-btn
              size="small"
              variant="text"
              color="red-darken-3"
              type="button"
              :title="`Delete mapping`"
              @click.stop="removeMapping(mi)"
              :prepend-icon="mdiTrashCanOutline"
            >
              Delete mapping
            </v-btn>

            <v-btn
              size="small"
              :prepend-icon="mdiSourceBranch"
              variant="text"
              type="button"
              @click="onAddMapping"
            >
              Add mapping
            </v-btn>
          </div>
          <v-divider
            v-if="mi < task.mappings.length - 1"
            class="mapping-actions"
          />
        </template>
      </div>

      <div class="mapping-actions" v-if="task.mappings.length === 0">
        <v-btn
          size="small"
          :prepend-icon="mdiSourceBranch"
          variant="text"
          type="button"
          @click="onAddMapping"
        >
          Add mapping
        </v-btn>
      </div>
    </template>
  </v-form>

  <v-dialog
    v-if="!isAggregationTask"
    v-model="datastreamSelectorOpen"
    width="75rem"
  >
    <DatastreamSelectorCard
      card-title="Select a target datastream"
      @selected-datastream="onTargetSelected"
      @close="datastreamSelectorOpen = false"
      enforce-unique-selections
      :draft-datastreams="draftDatastreams"
    />
  </v-dialog>

  <v-dialog
    v-if="isAggregationTask"
    v-model="aggregationDatastreamSelectorOpen"
    width="75rem"
  >
    <DatastreamSelectorCard
      :card-title="
        aggregationSelectorRole === 'source'
          ? 'Select source datastream'
          : 'Select target datastream'
      "
      @selected-datastream="onAggregationDatastreamSelected"
      @close="aggregationDatastreamSelectorOpen = false"
      :enforce-unique-selections="aggregationSelectorRole === 'target'"
      :draft-datastreams="
        aggregationSelectorRole === 'target' ? draftDatastreams : undefined
      "
    />
  </v-dialog>
</template>

<script setup lang="ts">
import type { Mapping, MappingPath, Task } from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'
import { storeToRefs } from 'pinia'
import { DatastreamExtended } from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import {
  mdiArrowRight,
  mdiImport,
  mdiPlus,
  mdiPlusCircleOutline,
  mdiSourceBranch,
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
} = storeToRefs(orchestrationStore)
const { ensureWorkspaceDatastreams } = orchestrationStore
const isAggregationTask = computed(
  () => ((task.value as any)?.type ?? 'ETL') === 'Aggregation'
)
const aggregationStatisticOptions = [
  { title: 'Simple mean', value: 'simple_mean' },
  { title: 'Time-weighted daily mean', value: 'time_weighted_daily_mean' },
  { title: 'Last value of day', value: 'last_value_of_day' },
]
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
const aggregationSourceMissing = ref(false)
const aggregationTargetMissing = ref(false)
const aggregationStatisticMissing = ref(false)

function hasTargetError(mi: number, pi: number) {
  return showErrors.value && missingTargetKeys.value.has(`${mi}:${pi}`)
}

function ensureAggregationTransformation(path: MappingPath): any {
  if (!Array.isArray(path.dataTransformations)) path.dataTransformations = []
  const existing = path.dataTransformations.find(
    (t: any) => t?.type === 'aggregation'
  ) as any
  const transform =
    existing ??
    ({
      type: 'aggregation',
      aggregationStatistic: 'simple_mean',
      timezoneMode: 'fixedOffset',
      timezone: '-0700',
    } as any)

  if (!existing) path.dataTransformations = [transform]
  return transform
}

function getAggregationStatistic(path: MappingPath) {
  return (
    ensureAggregationTransformation(path).aggregationStatistic || 'simple_mean'
  )
}

function setAggregationStatistic(path: MappingPath, value: string) {
  const transform = ensureAggregationTransformation(path)
  transform.aggregationStatistic = value || 'simple_mean'
  path.dataTransformations = [transform]
  aggregationStatisticMissing.value = false
}

function ensureSinglePath(mapping: Mapping) {
  if (!Array.isArray(mapping.paths) || mapping.paths.length === 0) {
    mapping.paths = [{ targetIdentifier: '', dataTransformations: [] }]
  }
  if (mapping.paths.length > 1) mapping.paths = [mapping.paths[0]]
  if (!Array.isArray(mapping.paths[0].dataTransformations)) {
    mapping.paths[0].dataTransformations = []
  }
  return mapping.paths[0]
}

function enforceMappingShape() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }
  if (!task.value.mappings.length && isAggregationTask.value) {
    task.value.mappings.push(createEmptyMapping())
  }

  task.value.mappings.forEach((mapping: any) => {
    const path = ensureSinglePath(mapping)
    if (isAggregationTask.value) ensureAggregationTransformation(path)
  })
}

function ensureInitialTaskMappings() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }

  if (isAggregationTask.value) return
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

  if (isAggregationTask.value) {
    enforceMappingShape()
    aggregationSourceMissing.value = false
    aggregationTargetMissing.value = false
    aggregationStatisticMissing.value = false

    task.value.mappings.forEach((mapping: any) => {
      const path = mapping?.paths?.[0] as any
      const statistic = path?.dataTransformations?.[0]?.aggregationStatistic

      if (!mapping?.sourceIdentifier) aggregationSourceMissing.value = true
      if (!path?.targetIdentifier) aggregationTargetMissing.value = true
      if (typeof statistic !== 'string' || statistic.trim().length === 0) {
        aggregationStatisticMissing.value = true
      }
    })

    if (
      aggregationSourceMissing.value ||
      aggregationTargetMissing.value ||
      aggregationStatisticMissing.value
    ) {
      ok = false
    }
    missingTargetKeys.value = new Set<string>()
    return ok
  }

  aggregationSourceMissing.value = false
  aggregationTargetMissing.value = false
  aggregationStatisticMissing.value = false

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
const aggregationDatastreamSelectorOpen = ref(false)
const aggregationSelectorRole = ref<'source' | 'target'>('source')
const aggregationSelectorMi = ref<number | null>(null)
const aggregationSelectorPi = ref<number | null>(null)

function datastreamNameById(id: string | number | undefined | null) {
  if (id === undefined || id === null || `${id}` === '') return ''
  const key = String(id)
  return (
    workspaceDatastreams.value.find((d) => d.id === key)?.name ||
    linkedDatastreams.value.find((d) => d.id === key)?.name ||
    draftDatastreams.value.find((d) => String(d.id) === key)?.name ||
    ''
  )
}

function openTargetSelector(mi: number, pi: number) {
  if (isAggregationTask.value) return
  activeMi.value = mi
  activePi.value = pi
  datastreamSelectorOpen.value = true
}

function openAggregationDatastreamSelector(
  role: 'source' | 'target',
  mi: number,
  pi: number
) {
  if (!isAggregationTask.value) return
  aggregationSelectorRole.value = role
  aggregationSelectorMi.value = mi
  aggregationSelectorPi.value = pi
  aggregationDatastreamSelectorOpen.value = true
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

function onAggregationDatastreamSelected(event: DatastreamExtended) {
  const mi = aggregationSelectorMi.value
  const pi = aggregationSelectorPi.value
  if (mi == null || pi == null) return

  const mapping = task.value.mappings[mi] as any
  const path = mapping?.paths?.[pi]
  if (!mapping || !path) return

  if (aggregationSelectorRole.value === 'source') {
    mapping.sourceIdentifier = event.id
    aggregationSourceMissing.value = false
  } else {
    path.targetIdentifier = event.id
    draftDatastreams.value = [event, ...draftDatastreams.value]
    syncDraftDatastreams()
    aggregationTargetMissing.value = false
  }

  aggregationSelectorMi.value = null
  aggregationSelectorPi.value = null
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

  if (isAggregationTask.value) {
    ensureAggregationTransformation(mapping.paths[0])
  }

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
    if (isAggregationTask.value) enforceMappingShape()
  },
  { immediate: true }
)

watch(isAggregationTask, () => {
  ensureInitialTaskMappings()
  if (isAggregationTask.value) enforceMappingShape()
})

watch(
  resolvedWorkspaceId,
  async (workspaceId) => {
    if (!workspaceId) return
    try {
      await ensureWorkspaceDatastreams(workspaceId)
    } catch (error) {
      console.error('Error fetching workspace datastreams', error)
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
  margin-left: calc(50% + 34px);
}
.etl-mapping-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px minmax(0, 1fr) 44px;
  gap: 5px;
  align-items: start;
}
.etl-mapping-source,
.etl-mapping-target {
  min-width: 0;
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
  justify-content: flex-start;
  border-style: dashed;
  border-width: 2px;
  border-color: #1565c0;
  color: #1565c0;
  background: #fdfdff;
  font-size: 0.84rem;
  padding-inline: 12px;
}
.etl-target-btn-error {
  border-color: #d32f2f;
  color: #d32f2f;
}
.etl-target-btn-selected {
  border-style: solid;
  background: #f6f9ff;
  color: #1c1b1f;
}
.etl-target-btn-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
}
.etl-target-btn :deep(.v-btn__content) {
  justify-content: flex-start;
  width: 100%;
  overflow: hidden;
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
}

.swimlanes {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  column-gap: 12px;
  row-gap: 8px;
  margin-bottom: 12px;
}
.swimlanes-aggregation {
  --aggregation-statistic-width: 18rem;
  grid-template-columns:
    minmax(0, 1fr)
    fit-content(var(--aggregation-statistic-width))
    minmax(0, 1fr);
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
  transition: transform 0.14s ease, box-shadow 0.14s ease,
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
}

.target-id {
  display: block;
  font-weight: 600;
  overflow-wrap: anywhere;
  white-space: normal;
}

.target-name {
  color: rgba(0, 0, 0, 0.66);
  display: block;
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
