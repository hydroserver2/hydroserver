<template>
  <aside v-if="sidebar.isOpen" class="datavis-filters-panel">
    <div class="flex h-full flex-col gap-4 px-4 py-4">
      <div class="flex items-center justify-between px-1">
        <div class="text-[11px] uppercase tracking-[0.25em] text-slate-500">
          Datastream Filters
        </div>
        <v-btn
          color="primary"
          variant="outlined"
          rounded="xl"
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
              :prepend-inner-icon="mdiBriefcaseOutline"
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
                    {{ item.name }}
                  </span>
                </v-chip>
              </template>
            </v-autocomplete>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-end text-xs text-slate-400">
            <span>{{ sortedMonitoringSites.length }}/{{ totalMonitoringSitesCount }}</span>
          </div>
          <div class="pt-2">
            <v-autocomplete
              v-model="selectedMonitoringSites"
              v-model:search="searchMonitoringSite"
              :items="sortedMonitoringSites"
              item-title="name"
              return-object
              multiple
              clearable
              :prepend-inner-icon="mdiMapMarkerOutline"
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
                  @click:close="selectedMonitoringSites.splice(index, 1)"
                >
                  <span class="truncate">
                    {{ item.name }}
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
                    {{ item }}
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
                    {{ item }}
                  </span>
                </v-chip>
              </template>
            </v-autocomplete>
          </div>
        </div>
      </div>
    </div>
  </aside>
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
  mdiBriefcaseOutline,
  mdiClose,
  mdiLayersOutline,
  mdiMapMarkerOutline,
} from '@mdi/js'

const {
  matchesSelectedObservedProperty,
  matchesSelectedProcessingLevel,
  matchesSelectedMonitoringSite,
  matchesSelectedWorkspace,
} = useDataVisStore()
const dataVisStore = useDataVisStore()
const {
  monitoringSites,
  datastreams,
  processingLevels,
  observedProperties,
  selectedMonitoringSites,
  selectedWorkspaces,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
} = storeToRefs(useDataVisStore())

const { workspaces } = storeToRefs(useWorkspaceStore())

const searchWorkspace = ref('')
const searchMonitoringSite = ref('')
const searchObservedProperty = ref('')
const searchProcessingLevel = ref('')
const totalWorkspacesCount = computed(() => {
  const workspaceIds = new Set<string>()
  datastreams.value.forEach((ds) => {
    const workspaceId = dataVisStore.monitoringSiteById.get(ds.monitoringSiteId)?.workspaceId
    if (workspaceId) {
      workspaceIds.add(workspaceId)
    }
  })

  return workspaces.value.filter((workspace) => workspaceIds.has(workspace.id))
    .length
})

const totalMonitoringSitesCount = computed(() => {
  const ids = new Set<string>()
  datastreams.value.forEach((ds) => {
    if (ds.monitoringSiteId) ids.add(ds.monitoringSiteId)
  })
  return monitoringSites.value.filter((monitoringSite) => ids.has(monitoringSite.id)).length
})

const totalObservedPropertyNamesCount = computed(() => {
  const names = new Set<string>()
  observedProperties.value.forEach((op) => {
    if (op.name) names.add(op.name)
  })
  return names.size
})

const totalProcessingLevelNamesCount = computed(() => {
  const names = new Set<string>()
  processingLevels.value.forEach((pl) => {
    if (pl.definition) names.add(pl.definition)
  })
  return names.size
})

// Only show list items that are referenced by at least one datastream
// Then mutually filter the lists by selected filters.
const sortedWorkspaces = computed(() => {
  const workspaceIds = new Set<string>()

  datastreams.value.forEach((ds) => {
    if (
      !matchesSelectedMonitoringSite(ds) ||
      !matchesSelectedObservedProperty(ds) ||
      !matchesSelectedProcessingLevel(ds)
    ) {
      return
    }

    const workspaceId = dataVisStore.monitoringSiteById.get(ds.monitoringSiteId)?.workspaceId
    if (workspaceId) workspaceIds.add(workspaceId)
  })

  return workspaces.value
    .filter((workspace) => workspaceIds.has(workspace.id))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedProcessingLevelNames = computed(() => {
  const names = new Set<string>()

  datastreams.value.forEach((ds) => {
    if (
      !matchesSelectedMonitoringSite(ds) ||
      !matchesSelectedObservedProperty(ds) ||
      !matchesSelectedWorkspace(ds)
    ) {
      return
    }

    const definition = dataVisStore.processingLevelById.get(
      ds.processingLevelId
    )?.definition
    if (definition) {
      names.add(definition)
    }
  })

  return [...names].sort()
})

const sortedMonitoringSites = computed(() => {
  const monitoringSiteIds = new Set<string>()

  datastreams.value.forEach((ds) => {
    if (
      !matchesSelectedObservedProperty(ds) ||
      !matchesSelectedProcessingLevel(ds) ||
      !matchesSelectedWorkspace(ds)
    ) {
      return
    }

    monitoringSiteIds.add(ds.monitoringSiteId)
  })

  return monitoringSites.value
    .filter((monitoringSite) => monitoringSiteIds.has(monitoringSite.id))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedObservedPropertyNames = computed(() => {
  const names = new Set<string>()

  datastreams.value.forEach((ds) => {
    if (
      !matchesSelectedMonitoringSite(ds) ||
      !matchesSelectedProcessingLevel(ds) ||
      !matchesSelectedWorkspace(ds)
    ) {
      return
    }

    const name = dataVisStore.observedPropertyById.get(
      ds.observedPropertyId
    )?.name
    if (name) {
      names.add(name)
    }
  })

  return [...names].sort()
})

const emit = defineEmits<{
  (e: 'drawer-change', value: boolean): void
}>()

const clearFilters = () => {
  selectedMonitoringSites.value = []
  selectedWorkspaces.value = []
  selectedObservedPropertyNames.value = []
  selectedProcessingLevelNames.value = []

  searchWorkspace.value = ''
  searchMonitoringSite.value = ''
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

/* Floating "island" card, matching the filter panel on Browse Monitoring
   Sites (BrowseFilterTool.vue) exactly: same radius, same translucent
   background, same shadow (--hs-shadow-float, sourced from Vuetify's own
   card shadow) instead of a flush, square-cornered drawer. Browse's panel
   is a real <v-card>, so it picks up that shadow from Vuetify directly;
   this is a plain element, so it's applied explicitly here. */
.datavis-filters-panel {
  width: 340px;
  max-width: 100%;
  flex-shrink: 0;
  min-height: 0;
  border-radius: var(--hs-radius-lg);
  background: var(--hs-surface-floating);
  box-shadow: var(--hs-shadow-float);
  color: var(--hs-text-primary);
  overflow: hidden;
  z-index: 1;
}

@media (max-width: 700px) {
  .datavis-filters-panel {
    position: absolute;
    inset: 0;
    width: auto;
    /* Fully opaque on mobile, where the panel covers the plot/table instead
       of a map, so underlying content doesn't show through. */
    background: var(--hs-surface);
    border-radius: 0;
    z-index: 30;
  }
}
</style>
