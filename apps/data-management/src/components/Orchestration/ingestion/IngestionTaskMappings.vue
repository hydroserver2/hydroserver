<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex flex-col gap-px">
      <h3 class="text-[0.67rem] tracking-[0.08em] uppercase font-extrabold text-[#4f4b59]">
        Data mapping
      </h3>
      <p class="text-[#5f5a67] text-[0.72rem] leading-[1.3]">
        Map each source field (CSV column or JSON key) to a HydroServer
        datastream.
      </p>
    </div>

    <v-alert
      v-if="showErrors && noMappingsError"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-3"
    >
      At least one source target mapping is required.
    </v-alert>

    <div class="flex flex-col gap-1">
      <div class="flex">
        <div class="font-extrabold uppercase tracking-[0.04em] text-[#4f4b59] text-[0.68rem]">
          Source field
        </div>
        <div class="etl-mappings-head-target font-extrabold uppercase tracking-[0.04em] text-[#4f4b59] text-[0.68rem]">
          Target datastream
        </div>
      </div>

      <template v-for="(m, mi) in task.mappings as any[]" :key="mi">
        <div
          class="grid grid-cols-[minmax(0,1fr)_42px_minmax(0,2fr)_44px] gap-[5px] items-center max-[640px]:grid-cols-1 max-[640px]:gap-[10px]"
        >
          <div class="etl-mapping-source min-w-0 self-center">
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

          <div
            class="flex items-center justify-center text-[#c0b8c9] min-h-[40px] max-[640px]:justify-start max-[640px]:min-h-0"
          >
            <v-icon :icon="mdiArrowRight" size="22" />
          </div>

          <div class="min-w-0 self-center">
            <v-btn
              v-if="!ensureSinglePath(m).targetIdentifier"
              variant="outlined"
              rounded="lg"
              type="button"
              class="etl-target-btn text-none"
              :class="{ 'etl-target-btn-error': hasTargetError(mi, 0) }"
              @click="openTargetSelector(mi, 0)"
            >
              <span class="inline-flex items-center gap-1.5 font-bold">
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
              <span class="block max-w-full leading-[1.25] py-[2px]">
                <span class="font-semibold text-[#1c1b1f] block [overflow-wrap:anywhere] whitespace-normal">
                  {{ datastreamNameById(ensureSinglePath(m).targetIdentifier) }}
                </span>
                <span
                  v-if="
                    datastreamThingNameById(
                      ensureSinglePath(m).targetIdentifier
                    )
                  "
                  class="text-[rgba(0,0,0,0.66)] block text-[0.78rem] [overflow-wrap:anywhere] whitespace-normal"
                >
                  {{
                    datastreamThingNameById(
                      ensureSinglePath(m).targetIdentifier
                    )
                  }}
                </span>
                <span class="text-[rgba(0,0,0,0.55)] block text-[0.72rem] [overflow-wrap:anywhere] whitespace-normal">
                  {{ String(ensureSinglePath(m).targetIdentifier) }}
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

          <div
            class="flex items-center justify-center min-h-[40px] max-[640px]:justify-start max-[640px]:min-h-0"
          >
            <v-btn
              icon
              variant="text"
              color="red-lighten-1"
              type="button"
              title="Delete mapping"
              @click.stop="removeMapping(mi)"
            >
              <v-icon :icon="mdiTrashCanOutline" size="22" />
            </v-btn>
          </div>
        </div>
      </template>

      <div class="mt-px">
        <v-btn
          variant="outlined"
          rounded="lg"
          type="button"
          class="text-none etl-add-mapping-btn"
          :prepend-icon="mdiPlus"
          @click="addMapping"
        >
          Add mapping
        </v-btn>
      </div>
    </div>
  </div>

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
import type { DatastreamExtended, Mapping, Task } from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'
import { rules } from '@/utils/rules'
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

const showErrors = ref(false)
const missingTargetKeys = ref<Set<string>>(new Set())
const noMappingsError = ref(false)
const datastreamSelectorOpen = ref(false)
const activeMappingIndex = ref<number | null>(null)
const activePathIndex = ref<number | null>(null)

const resolvedWorkspaceId = computed(() => {
  return (
    props.workspaceId ||
    (task.value as any)?.workspaceId ||
    (task.value as any)?.workspace?.id ||
    null
  )
})

function createEmptyMapping() {
  return {
    sourceIdentifier: '',
    paths: [
      {
        targetIdentifier: '',
        dataTransformations: [],
      },
    ],
  } as any
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

function ensureTaskMappings(addInitial = true) {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }

  task.value.mappings.forEach((mapping: any) => {
    ensureSinglePath(mapping)
  })

  if (addInitial && task.value.mappings.length === 0) {
    task.value.mappings.push(createEmptyMapping())
  }
}

function hasTargetError(mi: number, pi: number) {
  return showErrors.value && missingTargetKeys.value.has(`${mi}:${pi}`)
}

function datastreamById(id: string | number | undefined | null): any {
  if (id === undefined || id === null || `${id}` === '') return null
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

function datastreamNameById(id: string | number | undefined | null) {
  return datastreamById(id)?.name || ''
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
  activeMappingIndex.value = mi
  activePathIndex.value = pi
  datastreamSelectorOpen.value = true
}

function referencedTargetIds(): Set<string> {
  const ids = new Set<string>()
  for (const mapping of task.value.mappings as any[]) {
    const paths = Array.isArray(mapping.paths) ? mapping.paths : []
    for (const path of paths) {
      const id = path.targetIdentifier
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
  const mi = activeMappingIndex.value
  const pi = activePathIndex.value
  if (mi == null || pi == null) return

  const mapping = task.value.mappings[mi] as any
  const path = mapping?.paths?.[pi]
  if (!path) return

  path.targetIdentifier = event.id
  draftDatastreams.value = [event, ...draftDatastreams.value]
  syncDraftDatastreams()

  const key = `${mi}:${pi}`
  if (missingTargetKeys.value.has(key)) {
    const next = new Set(missingTargetKeys.value)
    next.delete(key)
    missingTargetKeys.value = next
  }

  activeMappingIndex.value = null
  activePathIndex.value = null
  datastreamSelectorOpen.value = false
}

function removeMapping(mi: number) {
  const mappings = task.value.mappings
  if (!Array.isArray(mappings) || mi < 0 || mi >= mappings.length) return
  mappings.splice(mi, 1)
  syncDraftDatastreams()
}

function addMapping() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }
  task.value.mappings.push(createEmptyMapping())
  noMappingsError.value = false
}

function validate() {
  ensureTaskMappings(false)
  showErrors.value = true
  noMappingsError.value = task.value.mappings.length === 0

  const nextMissingKeys = new Set<string>()
  task.value.mappings.forEach((mapping: any, mi) => {
    const path = ensureSinglePath(mapping)
    if (!path.targetIdentifier) nextMissingKeys.add(`${mi}:0`)
  })

  missingTargetKeys.value = nextMissingKeys
  return !noMappingsError.value && nextMissingKeys.size === 0
}

defineExpose({ ensureTaskMappings, validate })

watch(
  () => task.value,
  () => ensureTaskMappings(),
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
.etl-mappings-head-target {
  margin-left: calc((100% - 101px) / 3 + 52px);
}
@media (max-width: 640px) {
  .etl-mappings-head-target {
    margin-left: 0;
  }
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
.etl-target-btn :deep(.v-btn__content) {
  justify-content: flex-start;
  text-align: left;
  width: 100%;
  min-width: 0;
  overflow: visible;
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
</style>
