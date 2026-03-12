<template>
  <v-navigation-drawer
    v-model="sidebar.isOpen"
    width="400"
    class="datavis-filters-drawer border-r border-slate-200 bg-slate-50 text-slate-900"
  >
    <div class="flex h-full flex-col gap-4 px-4 py-4">
      <div class="flex items-center justify-between px-1">
        <div class="text-[11px] uppercase tracking-[0.25em] text-slate-500">
          Datastream Filters
        </div>
        <v-btn
          color="primary"
          variant="outlined"
          rounded
          :append-icon="mdiClose"
          class="text-xs"
          @click="clearFilters"
        >
          Clear filters
        </v-btn>
      </div>

      <div class="flex flex-1 flex-col gap-3 overflow-auto pr-1">
        <div>
          <div class="flex items-center justify-end text-xs text-slate-400">
            <span
              >{{ sortedWorkspaces.length }}/{{ totalWorkspacesCount }}</span
            >
          </div>
          <div class="pt-2">
            <v-autocomplete
              v-model="selectedWorkspaces"
              v-model:search="searchWorkspace"
              :items="sortedWorkspaces"
              item-title="name"
              return-object
              multiple
              clearable
              :prepend-inner-icon="mdiDomain"
              label="Workspaces"
              density="compact"
              variant="outlined"
              hide-details
              class="mt-2 [&_.v-field]:rounded-md [&_.v-field]:border [&_.v-field]:border-slate-200 [&_.v-field]:bg-white [&_.v-field]:text-slate-700 [&_.v-field-label]:text-slate-500"
            >
              <template #selection="{ item, index }">
                <v-chip
                  size="small"
                  closable
                  class="mr-1 mb-1 max-w-full"
                  @click:close="selectedWorkspaces.splice(index, 1)"
                >
                  <span class="truncate">
                    {{ item.title }}
                  </span>
                </v-chip>
              </template>
            </v-autocomplete>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-end text-xs text-slate-400">
            <span>{{ sortedThings.length }}/{{ totalThingsCount }}</span>
          </div>
          <div class="pt-2">
            <v-autocomplete
              v-model="selectedThings"
              v-model:search="searchThing"
              :items="sortedThings"
              item-title="name"
              return-object
              multiple
              clearable
              :prepend-inner-icon="mdiMapMarker"
              label="Sites"
              density="compact"
              variant="outlined"
              hide-details
              class="mt-2 [&_.v-field]:rounded-md [&_.v-field]:border [&_.v-field]:border-slate-200 [&_.v-field]:bg-white [&_.v-field]:text-slate-700 [&_.v-field-label]:text-slate-500"
            >
              <template #selection="{ item, index }">
                <v-chip
                  size="small"
                  closable
                  class="mr-1 mb-1 max-w-full"
                  @click:close="selectedThings.splice(index, 1)"
                >
                  <span class="truncate">
                    {{ item.title }}
                  </span>
                </v-chip>
              </template>
            </v-autocomplete>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-end text-xs text-slate-400">
            <span>
              {{ sortedObservedPropertyNames.length }}/{{
                totalObservedPropertyNamesCount
              }}
            </span>
          </div>
          <div class="pt-2">
            <v-autocomplete
              v-model="selectedObservedPropertyNames"
              v-model:search="searchObservedProperty"
              :items="sortedObservedPropertyNames"
              multiple
              clearable
              :prepend-inner-icon="mdiChartLine"
              label="Observed properties"
              density="compact"
              variant="outlined"
              hide-details
              class="mt-2 [&_.v-field]:rounded-md [&_.v-field]:border [&_.v-field]:border-slate-200 [&_.v-field]:bg-white [&_.v-field]:text-slate-700 [&_.v-field-label]:text-slate-500"
            >
              <template #selection="{ item, index }">
                <v-chip
                  size="small"
                  closable
                  class="mr-1 mb-1 max-w-full"
                  @click:close="selectedObservedPropertyNames.splice(index, 1)"
                >
                  <span class="truncate">
                    {{ item.title }}
                  </span>
                </v-chip>
              </template>
            </v-autocomplete>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-end text-xs text-slate-400">
            <span>
              {{ sortedProcessingLevelNames.length }}/{{
                totalProcessingLevelNamesCount
              }}
            </span>
          </div>
          <div class="pt-2">
            <v-autocomplete
              v-model="selectedProcessingLevelNames"
              v-model:search="searchProcessingLevel"
              :items="sortedProcessingLevelNames"
              multiple
              clearable
              :prepend-inner-icon="mdiLayersOutline"
              label="Processing levels"
              density="compact"
              variant="outlined"
              hide-details
              class="mt-2 [&_.v-field]:rounded-md [&_.v-field]:border [&_.v-field]:border-slate-200 [&_.v-field]:bg-white [&_.v-field]:text-slate-700 [&_.v-field-label]:text-slate-500"
            >
              <template #selection="{ item, index }">
                <v-chip
                  size="small"
                  closable
                  class="mr-1 mb-1 max-w-full"
                  @click:close="selectedProcessingLevelNames.splice(index, 1)"
                >
                  <span class="truncate">
                    {{ item.title }}
                  </span>
                </v-chip>
              </template>
            </v-autocomplete>
          </div>
        </div>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useDisplay } from 'vuetify/lib/framework.mjs'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { useSidebarStore } from '@/store/useSidebar'
import { useWorkspaceStore } from '@/store/workspaces'
import {
  mdiChartLine,
  mdiClose,
  mdiDomain,
  mdiLayersOutline,
  mdiMapMarker,
} from '@mdi/js'

const {
  matchesSelectedObservedProperty,
  matchesSelectedProcessingLevel,
  matchesSelectedThing,
  matchesSelectedWorkspace,
} = useDataVisStore()
const {
  things,
  datastreams,
  processingLevels,
  observedProperties,
  selectedThings,
  selectedWorkspaces,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
} = storeToRefs(useDataVisStore())

const { workspaces } = storeToRefs(useWorkspaceStore())

const searchWorkspace = ref('')
const searchThing = ref('')
const searchObservedProperty = ref('')
const searchProcessingLevel = ref('')
const totalWorkspacesCount = computed(() => {
  const thingIds = new Set<string>()
  datastreams.value.forEach((ds) => {
    if (ds.thingId) thingIds.add(ds.thingId)
  })

  const workspaceIds = new Set<string>()
  things.value.forEach((thing) => {
    if (thingIds.has(thing.id) && thing.workspaceId) {
      workspaceIds.add(thing.workspaceId)
    }
  })

  return workspaces.value.filter((workspace) => workspaceIds.has(workspace.id))
    .length
})

const totalThingsCount = computed(() => {
  const ids = new Set<string>()
  datastreams.value.forEach((ds) => {
    if (ds.thingId) ids.add(ds.thingId)
  })
  return things.value.filter((thing) => ids.has(thing.id)).length
})

const totalObservedPropertyNamesCount = computed(() => {
  const ids = new Set<string>()
  datastreams.value.forEach((ds) => {
    if (ds.observedPropertyId) ids.add(ds.observedPropertyId)
  })
  const names = new Set<string>()
  observedProperties.value.forEach((op) => {
    if (ids.has(op.id) && op.name) names.add(op.name)
  })
  return names.size
})

const totalProcessingLevelNamesCount = computed(() => {
  const ids = new Set<string>()
  datastreams.value.forEach((ds) => {
    if (ds.processingLevelId) ids.add(ds.processingLevelId)
  })
  const names = new Set<string>()
  processingLevels.value.forEach((pl) => {
    if (ids.has(pl.id) && pl.definition) names.add(pl.definition)
  })
  return names.size
})

// Only show list items that are referenced by at least one datastream
// Then mutually filter the lists by selected filters.
const sortedWorkspaces = computed(() => {
  const thingById = new Map(things.value.map((thing) => [thing.id, thing]))
  const workspaceIds = new Set<string>()

  datastreams.value.forEach((ds) => {
    if (
      !matchesSelectedThing(ds) ||
      !matchesSelectedObservedProperty(ds) ||
      !matchesSelectedProcessingLevel(ds)
    ) {
      return
    }

    const workspaceId = thingById.get(ds.thingId)?.workspaceId
    if (workspaceId) workspaceIds.add(workspaceId)
  })

  return workspaces.value
    .filter((workspace) => workspaceIds.has(workspace.id))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedProcessingLevelNames = computed(() => {
  const filteredPLs = processingLevels.value.filter((pl) => {
    const definition = pl.definition ?? ''
    return datastreams.value.some(
      (ds) =>
        ds.processingLevelId === pl.id &&
        matchesSelectedThing(ds) &&
        matchesSelectedObservedProperty(ds) &&
        matchesSelectedWorkspace(ds)
    )
  })
  const names = filteredPLs.map((pl) => pl.definition)
  return [...new Set(names)].sort()
})

const sortedThings = computed(() => {
  return things.value
    .filter((thing) =>
      datastreams.value.some(
        (ds) =>
          ds.thingId === thing.id &&
          matchesSelectedObservedProperty(ds) &&
          matchesSelectedProcessingLevel(ds) &&
          matchesSelectedWorkspace(ds)
      )
    )
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedObservedPropertyNames = computed(() => {
  const filteredProperties = observedProperties.value.filter((op) =>
    datastreams.value.some(
      (ds) =>
        ds.observedPropertyId === op.id &&
        matchesSelectedThing(ds) &&
        matchesSelectedProcessingLevel(ds) &&
        matchesSelectedWorkspace(ds)
    )
  )

  const names = filteredProperties.map((pl) => pl.name)
  return [...new Set(names)].sort()
})

const emit = defineEmits<{
  (e: 'drawer-change', value: boolean): void
}>()

const clearFilters = () => {
  selectedThings.value = []
  selectedWorkspaces.value = []
  selectedObservedPropertyNames.value = []
  selectedProcessingLevelNames.value = []

  searchWorkspace.value = ''
  searchThing.value = ''
  searchObservedProperty.value = ''
  searchProcessingLevel.value = ''
}

const { smAndDown } = useDisplay()
const sidebar = useSidebarStore()

onMounted(() => {
  if (!sidebar.isExplicit) {
    sidebar.setOpen(!smAndDown.value)
  }
})

watch(smAndDown, (isMobile) => {
  if (!sidebar.isExplicit) {
    sidebar.setOpen(!isMobile)
  }
})

watch(
  () => sidebar.isOpen,
  (value) => {
    emit('drawer-change', value)
  }
)
</script>

<style scoped>
:deep(.datastream-filter-autocomplete .v-field__input) {
  flex-wrap: wrap;
}

:deep(.datastream-filter-autocomplete .v-chip) {
  max-width: 100%;
}

:deep(.datastream-filter-autocomplete .v-chip__content) {
  display: block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.datavis-filters-drawer {
  z-index: 1;
}

</style>
