<template>
  <div
    class="browse-filter-tool"
    :class="{ 'browse-filter-tool--expanded': isExpanded }"
  >
    <v-btn
      v-if="!isExpanded"
      class="filter-chip"
      elevation="8"
      rounded="pill"
      color="surface"
      @click="setExpanded(true)"
    >
      <v-icon :icon="mdiMagnify" size="16" color="primary" />
      <span class="filter-chip-label">Sites</span>
      <span class="filter-chip-count">
        {{ monitoringSitesLoaded ? `(${availableSites.length})` : '...' }}
      </span>
    </v-btn>

    <v-card v-else class="filter-panel" elevation="10">
      <div class="filter-header">
        <h1>Monitoring sites</h1>

        <div class="filter-header-actions">
          <v-btn
            v-if="showRegisterSite"
            class="register-site-button"
            color="primary"
            variant="flat"
            rounded="xl"
            data-testid="register-site-button"
            aria-label="Create Site"
            :disabled="!canRegisterSite"
            :title="
              canRegisterSite
                ? 'Create Site'
                : 'You need site creation permission in a workspace to create a site'
            "
            @click="$emit('register-site')"
          >
            <v-icon :icon="mdiPlus" size="16" />
            Create Site
          </v-btn>

          <v-btn
            icon
            variant="text"
            color="default"
            size="34"
            aria-label="Collapse site filters"
            @click="setExpanded(false)"
          >
            <v-icon :icon="mdiChevronLeft" size="20" />
          </v-btn>
        </div>
      </div>

      <div v-show="filtersVisible" class="filter-controls">
        <section class="filter-control-group" aria-label="Filter sites">
          <v-text-field
            v-model="siteSearch"
            class="site-search"
            name="browse-site-search"
            placeholder="Search sites"
            aria-label="Search sites"
            :prepend-inner-icon="mdiMagnify"
            clearable
            hide-details
            density="compact"
            color="primary"
            autocomplete="off"
            :disabled="!monitoringSitesLoaded"
            @keydown.enter.prevent="onSiteSearchEnter"
            @click:clear="siteSearch = ''"
          />

          <div
            class="workspace-filter-row"
            :class="{
              'workspace-filter-row--with-my-sites': showMySitesFilter,
            }"
          >
            <v-autocomplete
              v-model="selectedWorkspaces"
              :items="availableWorkspaces"
              class="workspace-filter"
              name="browse-workspace-filter"
              label="Workspaces"
              item-title="name"
              return-object
              multiple
              clearable
              hide-details
              density="compact"
              color="primary"
              :prepend-inner-icon="mdiBriefcaseOutline"
              :disabled="!monitoringSitesLoaded"
            >
              <template v-slot:selection="{ item, index }">
                <v-chip
                  v-if="index < 2"
                  size="small"
                  closable
                  @click:close="selectedWorkspaces.splice(index, 1)"
                >
                  <span>{{ item.name }}</span>
                </v-chip>
                <span
                  v-else-if="index === 2"
                  class="text-caption text-medium-emphasis ms-1"
                >
                  +{{ selectedWorkspaces.length - 2 }} more
                </span>
              </template>
            </v-autocomplete>

            <v-btn
              v-if="showMySitesFilter"
              class="my-sites-filter"
              color="primary"
              :variant="showOnlyMySites ? 'tonal' : 'outlined'"
              :aria-pressed="showOnlyMySites"
              data-testid="my-sites-filter"
              title="Show only sites in my workspaces"
              @click="showOnlyMySites = !showOnlyMySites"
            >
              <v-icon :icon="mdiAccountOutline" size="16" />
              My sites
            </v-btn>
          </div>

          <section v-if="availableSiteTypes.length" class="filter-section">
            <div class="filter-section-title">Site type</div>
            <div class="chip-grid">
              <v-btn
                v-for="type in availableSiteTypes"
                :key="type"
                class="filter-pill"
                :class="{ selected: selectedSiteTypes.includes(type) }"
                :variant="
                  selectedSiteTypes.includes(type) ? 'tonal' : 'outlined'
                "
                color="default"
                rounded="pill"
                @click="toggleSiteType(type)"
              >
                <v-icon
                  :icon="getSiteTypeIcon(type)"
                  :color="
                    selectedSiteTypes.includes(type) ? 'primary' : 'default'
                  "
                  size="16"
                />
                <span>{{ type }}</span>
              </v-btn>
            </div>
          </section>

          <section v-if="availableTagKeys.length" class="filter-section">
            <div class="filter-section-title">Additional metadata</div>
            <div class="metadata-filter-row">
              <v-autocomplete
                v-model="selectedTagKey"
                :items="availableTagKeys"
                class="metadata-filter"
                name="browse-metadata-key-filter"
                label="Key"
                clearable
                hide-details
                density="compact"
                color="primary"
                :prepend-inner-icon="mdiTagOutline"
                @update:model-value="selectedTagValues = []"
              />

              <v-autocomplete
                v-model="selectedTagValues"
                :items="availableTagValues"
                class="metadata-filter"
                name="browse-metadata-value-filter"
                label="Value"
                multiple
                clearable
                hide-details
                density="compact"
                color="primary"
                :disabled="!selectedTagKey"
              >
                <template v-slot:selection="{ item, index }">
                  <span v-if="index === 0" class="metadata-value-selection">
                    <span class="metadata-value-label">{{ item }}</span>
                    <span
                      v-if="selectedTagValues.length > 1"
                      class="metadata-value-count text-medium-emphasis"
                    >
                      +{{ selectedTagValues.length - 1 }}
                    </span>
                  </span>
                </template>
              </v-autocomplete>
            </div>
          </section>
        </section>

        <section
          class="filter-control-group"
          aria-labelledby="marker-colors-heading"
        >
          <div id="marker-colors-heading" class="filter-group-title">
            Color markers by
          </div>
          <div
            class="color-mode-buttons"
            role="group"
            aria-label="Color markers by"
          >
            <v-btn
              class="color-mode-button"
              color="grey-darken-1"
              size="small"
              :variant="markerColorMode === 'workspace' ? 'tonal' : 'outlined'"
              :aria-pressed="markerColorMode === 'workspace'"
              @click="toggleMarkerColorMode('workspace')"
            >
              Workspace
            </v-btn>
            <v-btn
              class="color-mode-button"
              color="grey-darken-1"
              size="small"
              :variant="markerColorMode === 'type' ? 'tonal' : 'outlined'"
              :aria-pressed="markerColorMode === 'type'"
              @click="toggleMarkerColorMode('type')"
            >
              Site type
            </v-btn>
            <v-btn
              class="color-mode-button"
              color="grey-darken-1"
              size="small"
              :variant="markerColorMode === 'metadata' ? 'tonal' : 'outlined'"
              :aria-pressed="markerColorMode === 'metadata'"
              :disabled="!availableTagKeys.length"
              @click="toggleMarkerColorMode('metadata')"
            >
              Metadata
            </v-btn>
          </div>

          <v-autocomplete
            v-if="markerColorMode === 'metadata'"
            v-model="colorTagKey"
            :items="availableTagKeys"
            class="color-tag-filter"
            name="browse-marker-color-tag"
            label="Metadata tag"
            data-testid="marker-color-tag-select"
            clearable
            hide-details
            density="compact"
            color="primary"
            :prepend-inner-icon="mdiTagOutline"
          />
        </section>
      </div>

      <v-divider v-if="filtersVisible" />

      <div class="site-list">
        <div class="site-list-header">
          <div class="site-list-count">
            {{
              monitoringSitesLoaded ? `${availableSites.length} sites` : 'Loading sites'
            }}
          </div>

          <div class="site-list-actions">
            <v-btn
              v-if="hasActiveFilters"
              class="reset-filters-btn"
              variant="text"
              color="primary"
              size="small"
              :prepend-icon="mdiFilterOffOutline"
              title="Clear all filters"
              @click="onClearFilters"
            >
              Reset
            </v-btn>

            <v-btn
              class="toggle-filters-btn"
              variant="text"
              color="primary"
              size="small"
              :aria-expanded="filtersVisible"
              @click="filtersVisible = !filtersVisible"
            >
              {{ filtersVisible ? 'Hide Filters' : 'Show Filters' }}
            </v-btn>
          </div>
        </div>

        <div v-if="!monitoringSitesLoaded" class="site-list-items">
          <div v-for="index in 8" :key="index" class="site-row skeleton-row">
            <span class="site-row-icon skeleton-icon" />

            <span class="site-row-text">
              <span class="skeleton-line skeleton-line--name" />
              <span class="skeleton-line skeleton-line--workspace" />
            </span>
          </div>
        </div>

        <div v-else-if="availableSites.length" class="site-list-items">
          <div
            v-for="site in availableSites"
            :key="site.id"
            class="site-row"
            :class="{ selected: site.id === selectedSiteId }"
            :data-site-id="site.id"
          >
            <button
              type="button"
              class="site-row-main"
              @click="$emit('select-site', site.id)"
            >
              <span class="site-row-icon">
                <v-icon :icon="getSiteTypeIcon(site.type)" size="20" />
              </span>

              <span class="site-row-text">
                <span class="site-row-name">{{ site.name }}</span>
                <span class="site-row-workspace">
                  <span v-if="site.code" class="site-row-code">
                    {{ site.code }}
                  </span>
                  <span v-if="site.code" aria-hidden="true">
                    ·
                  </span>
                  {{ getWorkspaceName(site.workspaceId) }}
                </span>
              </span>
            </button>

            <div
              v-if="canEditSite(site) || canDeleteSite(site)"
              class="site-row-actions"
            >
              <v-btn
                v-if="canEditSite(site)"
                icon
                class="site-row-action"
                variant="text"
                color="primary"
                size="28"
                :aria-label="`Edit ${site.name}`"
                :data-testid="`edit-browse-site-${site.id}`"
                @click.stop="$emit('edit-site', site)"
              >
                <v-icon :icon="mdiPencilOutline" size="17" />
              </v-btn>

              <v-btn
                v-if="canDeleteSite(site)"
                icon
                class="site-row-action"
                variant="text"
                color="error"
                size="28"
                :aria-label="`Delete ${site.name}`"
                :data-testid="`delete-browse-site-${site.id}`"
                @click.stop="$emit('delete-site', site)"
              >
                <v-icon :icon="mdiTrashCanOutline" size="17" />
              </v-btn>
            </div>
          </div>
        </div>

        <div v-else class="empty-sites">No sites match these filters.</div>
      </div>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { useVocabularyStore } from '@/composables/useVocabulary'
import {
  buildBrowseFilterQuery,
  filterMonitoringSiteMarkers,
  parseBrowseFilterQuery,
} from '@/utils/browseFilters'
import type { MarkerColorMode } from '@/utils/browseFilters'
import {
  buildSiteTypeIconRules,
  getSiteTypeIcon as resolveSiteTypeIcon,
} from '@/utils/siteTypeIcons'
import hs, { Workspace } from '@hydroserver/client'
import type { MonitoringSiteMapSummary } from '@/types'
import {
  mdiAccountOutline,
  mdiBriefcaseOutline,
  mdiChevronLeft,
  mdiFilterOffOutline,
  mdiMagnify,
  mdiPencilOutline,
  mdiPlus,
  mdiTagOutline,
  mdiTrashCanOutline,
} from '@mdi/js'

const route = useRoute()
const router = useRouter()
const { siteTypeIcons } = storeToRefs(useVocabularyStore())

const selectedSiteTypes = ref<string[]>([])
const selectedWorkspaces = ref<Workspace[]>([])
const selectedTagKey = ref('')
const selectedTagValues = ref<string[]>([])
const showOnlyMySites = ref(false)
const markerColorMode = ref<MarkerColorMode>('none')
const colorTagKey = ref('')
const siteSearch = ref('')
const workspaces = ref<Workspace[]>([])
const workspacesLoaded = ref(false)
const isExpanded = ref(true)
const filtersVisible = ref(true)
const isApplyingRouteState = ref(false)
const hasAppliedInitialRouteState = ref(false)
let routeApplyId = 0

const emit = defineEmits<{
  filter: [MonitoringSiteMapSummary[]]
  'select-site': [string | undefined]
  'color-settings': [
    {
      mode: MarkerColorMode
      key: string
      labels: Record<string, string>
    },
  ]
  'register-site': []
  'edit-site': [MonitoringSiteMapSummary]
  'delete-site': [MonitoringSiteMapSummary]
}>()

const props = defineProps({
  monitoringSites: {
    type: Array as () => MonitoringSiteMapSummary[],
    required: true,
  },
  monitoringSitesLoaded: {
    type: Boolean,
    default: false,
  },
  selectedSiteId: {
    type: String,
    default: undefined,
  },
  showMySitesFilter: {
    type: Boolean,
    default: false,
  },
  myWorkspaceIds: {
    type: Array as () => string[],
    default: () => [],
  },
  showRegisterSite: {
    type: Boolean,
    default: false,
  },
  canRegisterSite: {
    type: Boolean,
    default: false,
  },
  editableWorkspaceIds: {
    type: Array as () => string[],
    default: () => [],
  },
  deletableWorkspaceIds: {
    type: Array as () => string[],
    default: () => [],
  },
})

const routeState = parseBrowseFilterQuery(route.query)
if (routeState.drawer !== null) {
  isExpanded.value = routeState.drawer
}

const sortedMonitoringSites = computed(() =>
  [...props.monitoringSites].sort((a, b) => a.name.localeCompare(b.name))
)

const workspaceById = computed(
  () => new Map(workspaces.value.map((workspace) => [workspace.id, workspace]))
)

const searchNeedle = computed(() =>
  (siteSearch.value ?? '').trim().toLowerCase()
)

const monitoringSitesMatchingSearch = computed(() => {
  if (!searchNeedle.value) return sortedMonitoringSites.value

  return sortedMonitoringSites.value.filter((monitoringSite) => {
    const workspaceName = getWorkspaceName(monitoringSite.workspaceId)
    return [
      monitoringSite.name,
      monitoringSite.code,
      monitoringSite.type,
      workspaceName,
    ].some((value) => value.toLowerCase().includes(searchNeedle.value))
  })
})

const monitoringSitesMatchingMySites = computed(() => {
  if (!showOnlyMySites.value) return monitoringSitesMatchingSearch.value

  const workspaceIds = new Set(props.myWorkspaceIds)
  return monitoringSitesMatchingSearch.value.filter((monitoringSite) =>
    workspaceIds.has(monitoringSite.workspaceId)
  )
})

const availableSites = computed(() =>
  filterMonitoringSiteMarkers(
    monitoringSitesMatchingMySites.value,
    selectedWorkspaces.value,
    selectedSiteTypes.value,
    undefined,
    selectedTagKey.value,
    selectedTagValues.value
  )
)

const availableWorkspaces = computed(() => {
  const workspaceIds = new Set(
    filterMonitoringSiteMarkers(
      monitoringSitesMatchingMySites.value,
      [],
      selectedSiteTypes.value,
      undefined,
      selectedTagKey.value,
      selectedTagValues.value
    ).map((monitoringSite) => monitoringSite.workspaceId)
  )

  return workspaces.value.filter((workspace) => workspaceIds.has(workspace.id))
})

const availableSiteTypes = computed(() => {
  const siteTypes = new Set(
    filterMonitoringSiteMarkers(
      monitoringSitesMatchingMySites.value,
      selectedWorkspaces.value,
      [],
      undefined,
      selectedTagKey.value,
      selectedTagValues.value
    ).map((monitoringSite) => monitoringSite.type)
  )

  return [...siteTypes].filter(Boolean).sort((a, b) => a.localeCompare(b))
})

const monitoringSitesMatchingPrimaryFilters = computed(() =>
  filterMonitoringSiteMarkers(
    monitoringSitesMatchingMySites.value,
    selectedWorkspaces.value,
    selectedSiteTypes.value
  )
)

const availableTagKeys = computed(() => {
  const keys = new Set(
    monitoringSitesMatchingPrimaryFilters.value.flatMap((monitoringSite) =>
      monitoringSite.tags.map((tag) => tag.key)
    )
  )
  return [...keys].filter(Boolean).sort((a, b) => a.localeCompare(b))
})

const availableTagValues = computed(() => {
  if (!selectedTagKey.value) return []
  const values = new Set(
    monitoringSitesMatchingPrimaryFilters.value.flatMap((monitoringSite) =>
      monitoringSite.tags
        .filter((tag) => tag.key === selectedTagKey.value)
        .map((tag) => tag.value)
    )
  )
  return [...values].filter(Boolean).sort((a, b) => a.localeCompare(b))
})

const hasActiveFilters = computed(
  () =>
    Boolean((siteSearch.value ?? '').trim()) ||
    selectedWorkspaces.value.length > 0 ||
    selectedSiteTypes.value.length > 0 ||
    showOnlyMySites.value ||
    Boolean(selectedTagKey.value) ||
    selectedTagValues.value.length > 0
)

const getWorkspaceName = (workspaceId: string) =>
  workspaceById.value.get(workspaceId)?.name || 'Workspace'

const editableWorkspaceIdSet = computed(
  () => new Set(props.editableWorkspaceIds)
)
const deletableWorkspaceIdSet = computed(
  () => new Set(props.deletableWorkspaceIds)
)
const canEditSite = (site: MonitoringSiteMapSummary) =>
  editableWorkspaceIdSet.value.has(site.workspaceId)
const canDeleteSite = (site: MonitoringSiteMapSummary) =>
  deletableWorkspaceIdSet.value.has(site.workspaceId)

const siteTypeIconRules = computed(() =>
  buildSiteTypeIconRules(siteTypeIcons.value)
)

const getSiteTypeIcon = (type: string) =>
  resolveSiteTypeIcon(type, siteTypeIconRules.value)

const toggleSiteType = (type: string) => {
  selectedSiteTypes.value = selectedSiteTypes.value.includes(type)
    ? selectedSiteTypes.value.filter((selected) => selected !== type)
    : [...selectedSiteTypes.value, type]
}

const setExpanded = (value: boolean) => {
  isExpanded.value = value
}

const toggleMarkerColorMode = (mode: Exclude<MarkerColorMode, 'none'>) => {
  markerColorMode.value = markerColorMode.value === mode ? 'none' : mode
}

// Let the user quickly jump to a site: typing a query and pressing Enter
// selects the first match while leaving the search field focused and intact.
const onSiteSearchEnter = () => {
  const firstSite = availableSites.value[0]
  if (firstSite) {
    emit('select-site', firstSite.id)
  }
}

const emitFilteredMonitoringSites = () => {
  emit('filter', availableSites.value)
}

const querySignature = (query: Record<string, unknown>) =>
  JSON.stringify(
    Object.keys(query)
      .sort()
      .map((key) => [key, query[key]])
  )

const syncRouteFromSelection = async (siteId = props.selectedSiteId) => {
  if (isApplyingRouteState.value || !hasAppliedInitialRouteState.value) return

  const query = buildBrowseFilterQuery(route.query, {
    siteId,
    searchText: siteSearch.value,
    workspaceIds: selectedWorkspaces.value.map((workspace) => workspace.id),
    siteTypes: selectedSiteTypes.value,
    tagKey: selectedTagKey.value,
    tagValues: selectedTagValues.value,
    mySites: showOnlyMySites.value,
    colorBy: markerColorMode.value,
    colorTagKey: colorTagKey.value,
    drawer: isExpanded.value,
  })

  if (querySignature(query) === querySignature(route.query)) return

  await router.replace({
    name: route.name || 'Browse',
    params: route.params,
    query,
  })
}

const applyRouteState = async () => {
  if (!props.monitoringSitesLoaded || !workspacesLoaded.value) return

  const applyId = ++routeApplyId
  const state = parseBrowseFilterQuery(route.query)
  isApplyingRouteState.value = true

  const linkedSiteId = state.siteIds[0]

  siteSearch.value = state.searchText
  selectedWorkspaces.value = state.workspaceIds.length
    ? workspaces.value.filter((workspace) =>
        state.workspaceIds.includes(workspace.id)
      )
    : []
  selectedSiteTypes.value = state.siteTypes
  selectedTagKey.value = state.tagKey
  selectedTagValues.value = state.tagValues
  showOnlyMySites.value = props.showMySitesFilter && state.mySites === true
  markerColorMode.value = state.colorBy ?? 'none'
  colorTagKey.value = state.colorTagKey

  if (state.drawer !== null) {
    isExpanded.value = state.drawer
  }

  if (linkedSiteId !== props.selectedSiteId) {
    emit('select-site', linkedSiteId)
  }

  await nextTick()
  if (applyId !== routeApplyId) return

  isApplyingRouteState.value = false
  hasAppliedInitialRouteState.value = true
  emitFilteredMonitoringSites()
  void syncRouteFromSelection(linkedSiteId)
}

const onClearFilters = () => {
  selectedSiteTypes.value = []
  selectedWorkspaces.value = []
  selectedTagKey.value = ''
  selectedTagValues.value = []
  showOnlyMySites.value = false
  siteSearch.value = ''
}

onMounted(async () => {
  workspaces.value = await hs.workspaces.listAllItems({
    order_by: ['name'],
    expand_related: true,
  })
  workspacesLoaded.value = true
  void applyRouteState()
})

watch(
  [
    selectedSiteTypes,
    selectedWorkspaces,
    selectedTagKey,
    selectedTagValues,
    showOnlyMySites,
    siteSearch,
  ],
  emitFilteredMonitoringSites,
  { deep: true }
)

watch(
  [
    selectedSiteTypes,
    selectedWorkspaces,
    selectedTagKey,
    selectedTagValues,
    showOnlyMySites,
    markerColorMode,
    colorTagKey,
    siteSearch,
    isExpanded,
  ],
  () => syncRouteFromSelection(),
  { deep: true }
)

watch(
  [markerColorMode, colorTagKey, workspaces],
  () =>
    emit('color-settings', {
      mode: markerColorMode.value,
      key:
        markerColorMode.value === 'metadata' ? (colorTagKey.value ?? '') : '',
      labels:
        markerColorMode.value === 'workspace'
          ? Object.fromEntries(
              workspaces.value.map((workspace) => [
                workspace.id,
                workspace.name,
              ])
            )
          : {},
    }),
  { deep: true, immediate: true }
)

watch(
  () => props.selectedSiteId,
  (siteId) => syncRouteFromSelection(siteId)
)

watch(
  () =>
    [
      route.query,
      props.monitoringSites,
      props.monitoringSitesLoaded,
      props.showMySitesFilter,
      props.myWorkspaceIds,
      workspacesLoaded.value,
    ] as const,
  applyRouteState,
  { deep: true }
)

// Drop any selected values that are no longer in the available set when the
// other filters narrow the options.
const pruneSelectionToAvailable = <T, A>(
  selected: Ref<T[]>,
  available: ComputedRef<A[]>,
  selectedKey: (item: T) => unknown,
  availableKey: (item: A) => unknown
) =>
  watch(available, (items) => {
    if (!props.monitoringSitesLoaded) return
    const availableKeys = new Set(items.map(availableKey))
    const pruned = selected.value.filter((item) =>
      availableKeys.has(selectedKey(item))
    )
    if (pruned.length !== selected.value.length) {
      selected.value = pruned
    }
  })

pruneSelectionToAvailable(
  selectedWorkspaces,
  availableWorkspaces,
  (workspace) => workspace.id,
  (workspace) => workspace.id
)

pruneSelectionToAvailable(
  selectedSiteTypes,
  availableSiteTypes,
  (type) => type,
  (type) => type
)

watch(availableTagKeys, (keys) => {
  if (selectedTagKey.value && !keys.includes(selectedTagKey.value)) {
    selectedTagKey.value = ''
  }
  if (colorTagKey.value && !keys.includes(colorTagKey.value)) {
    colorTagKey.value = ''
  }
  if (
    markerColorMode.value === 'metadata' &&
    !colorTagKey.value &&
    keys.length
  ) {
    colorTagKey.value = keys[0]
  }
})

watch(markerColorMode, (mode) => {
  if (mode === 'metadata' && !colorTagKey.value) {
    colorTagKey.value = availableTagKeys.value[0] ?? ''
  }
})

pruneSelectionToAvailable(
  selectedTagValues,
  availableTagValues,
  (value) => value,
  (value) => value
)
</script>

<style scoped>
.browse-filter-tool {
  width: min(38vw, 380px);
  min-width: 340px;
  max-height: calc(100% - 32px);
}

.browse-filter-tool--expanded {
  height: calc(100% - 32px);
}

.filter-chip {
  height: 38px;
  padding-inline: var(--hs-space-12);
  color: var(--hs-text-primary);
  box-shadow: 0 4px 16px rgba(22, 27, 34, 0.16) !important;
}

.filter-chip :deep(.v-btn__content) {
  gap: var(--hs-space-8);
  font-size: var(--hs-font-sm);
  font-weight: 700;
  letter-spacing: 0;
}

.filter-chip-count {
  color: var(--hs-text-secondary);
  font-weight: 600;
}

.filter-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: var(--hs-radius-lg);
  background: var(--hs-surface-floating);
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--hs-space-12);
  padding: var(--hs-space-16) var(--hs-space-20) var(--hs-space-10);
}

.filter-header h1 {
  margin: 0;
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 0;
}

.filter-header-actions {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
  flex-shrink: 0;
}

.register-site-button {
  padding-inline: var(--hs-space-16);
  font-size: var(--hs-font-sm);
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
}

.register-site-button :deep(.v-btn__content) {
  gap: var(--hs-space-6);
}

.filter-controls {
  display: flex;
  min-height: 0;
  flex: 0 1 auto;
  flex-direction: column;
  gap: var(--hs-space-10);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0 var(--hs-space-20) var(--hs-space-16);
}

.site-search :deep(.v-field),
.workspace-filter :deep(.v-field),
.metadata-filter :deep(.v-field),
.color-tag-filter :deep(.v-field) {
  border-radius: var(--hs-radius-md);
  font-size: var(--hs-font-sm);
}

.site-search :deep(.v-field__input),
.workspace-filter :deep(.v-field__input),
.metadata-filter :deep(.v-field__input),
.color-tag-filter :deep(.v-field__input) {
  font-size: var(--hs-font-sm);
}

.workspace-filter-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}

.workspace-filter-row--with-my-sites {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--hs-space-8);
}

.workspace-filter {
  min-width: 0;
}

.my-sites-filter {
  min-width: 0;
  height: 40px;
  border-radius: var(--hs-radius-md);
  padding-inline: var(--hs-space-10);
  font-size: var(--hs-font-sm);
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}

.my-sites-filter :deep(.v-btn__content) {
  gap: var(--hs-space-4);
}

.filter-control-group {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-10);
}

.filter-group-title {
  color: var(--hs-text-primary);
  font-size: var(--hs-font-sm);
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-8);
}

.filter-section-title {
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-2xs);
  font-weight: 700;
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.color-mode-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-4);
}

.color-mode-button {
  min-width: 0;
  height: 24px;
  flex: 0 0 auto;
  border-radius: var(--hs-radius-sm);
  padding-inline: var(--hs-space-6);
  font-size: var(--hs-font-sm);
  font-weight: 600;
  letter-spacing: 0;
}

.metadata-filter-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: var(--hs-space-8);
}

.metadata-filter {
  min-width: 0;
}

.metadata-filter :deep(.v-field),
.metadata-filter :deep(.v-field__input) {
  height: 40px;
}

.metadata-filter :deep(.v-field__input) {
  min-height: 40px;
  flex-wrap: nowrap;
  overflow: hidden;
}

.metadata-filter :deep(.v-autocomplete__selection) {
  min-width: 0;
  max-width: 100%;
}

.metadata-value-selection {
  display: flex;
  min-width: 0;
  max-width: 100%;
  align-items: center;
  gap: var(--hs-space-4);
  white-space: nowrap;
}

.metadata-value-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metadata-value-count {
  flex: 0 0 auto;
  font-size: var(--hs-font-sm);
}

.chip-grid {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: var(--hs-space-6);
  max-height: 102px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.chip-grid::-webkit-scrollbar {
  width: 6px;
}

.chip-grid::-webkit-scrollbar-track {
  border-radius: 3px;
  background: #dfe3e6;
}

.chip-grid::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: #9aa0a6;
}

.filter-pill {
  height: 30px;
  padding-inline: var(--hs-space-10);
  color: var(--hs-text-secondary);
  border-color: var(--hs-border);
  font-size: var(--hs-font-sm);
  font-weight: 600;
}

.filter-pill :deep(.v-btn__content) {
  gap: var(--hs-space-6);
  letter-spacing: 0;
}

.filter-pill.selected {
  /* The theme's actual primary, not a hand-picked near-miss blue — the
     border/background right below already correctly used it. */
  color: rgb(var(--v-theme-primary));
  border-color: rgba(33, 150, 243, 0.38);
  background: rgba(33, 150, 243, 0.1);
}

.reset-filters-btn {
  min-width: 0;
  padding-inline: var(--hs-space-8);
  font-size: var(--hs-font-2xs);
  font-weight: 600;
  letter-spacing: 0;
}

.reset-filters-btn :deep(.v-btn__prepend) {
  margin-inline-end: var(--hs-space-4);
}

.site-list {
  min-height: 140px;
  flex: 1 0 140px;
  overflow: hidden auto;
  padding: var(--hs-space-12) var(--hs-space-20) var(--hs-space-16);
}

.site-list-header {
  display: flex;
  min-height: 30px;
  align-items: center;
  justify-content: space-between;
  gap: var(--hs-space-8);
  margin-bottom: var(--hs-space-8);
}

.site-list-count {
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-2xs);
  font-weight: 700;
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.site-list-actions {
  display: flex;
  align-items: center;
  gap: var(--hs-space-2);
}

.toggle-filters-btn {
  min-width: 0;
  padding-inline: var(--hs-space-6);
  font-size: var(--hs-font-2xs);
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}

.site-list-items {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-2);
}

.site-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--hs-space-2);
  width: 100%;
  min-height: 46px;
  padding: var(--hs-space-2) 0;
  border-radius: var(--hs-radius-md);
  background: transparent;
  color: inherit;
}

.site-row:hover,
.site-row.selected {
  background: rgba(33, 150, 243, 0.1);
}

.site-row:hover .site-row-name,
.site-row.selected .site-row-name {
  color: rgb(var(--v-theme-primary));
}

.site-row-main {
  display: grid;
  min-width: 0;
  min-height: 42px;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: var(--hs-space-10);
  padding: var(--hs-space-4) 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}

.site-row-actions {
  display: flex;
  align-items: center;
  gap: var(--hs-space-2);
  padding-right: var(--hs-space-4);
  opacity: 0;
  transition: opacity 0.1s;
}

.site-row:hover .site-row-actions,
.site-row:focus-within .site-row-actions,
.site-row.selected .site-row-actions {
  opacity: 1;
}

.site-row-action {
  width: 28px;
  height: 28px;
  min-width: 28px;
}

.site-row-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--hs-radius-md);
  background: var(--hs-surface-muted);
  color: var(--hs-text-secondary);
}

.skeleton-row {
  grid-template-columns: 34px minmax(0, 1fr);
  gap: var(--hs-space-10);
  padding: var(--hs-space-6) 0;
  pointer-events: none;
}

.skeleton-icon,
.skeleton-line {
  position: relative;
  overflow: hidden;
  background: #e8ecf1;
}

.skeleton-icon::after,
.skeleton-line::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.75),
    transparent
  );
  content: '';
  transform: translateX(-100%);
  animation: browse-skeleton-shimmer 1.35s ease-in-out infinite;
}

.skeleton-line {
  display: block;
  height: 10px;
  border-radius: var(--hs-radius-pill);
}

.skeleton-line--name {
  width: min(72%, 190px);
}

.skeleton-line--workspace {
  width: min(48%, 140px);
}

.site-row-text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--hs-space-2);
}

.site-row-name,
.site-row-workspace {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-row-code {
  font-family: 'Roboto Mono', monospace;
  font-size: var(--hs-font-2xs);
}

.site-row-name {
  color: var(--hs-text-primary);
  font-size: var(--hs-font-sm);
  font-weight: 600;
  line-height: 1.25;
}

.site-row-workspace {
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-2xs);
  font-weight: 500;
}

.empty-sites {
  display: flex;
  min-height: 120px;
  align-items: center;
  justify-content: center;
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: 600;
  text-align: center;
}

@keyframes browse-skeleton-shimmer {
  100% {
    transform: translateX(100%);
  }
}

@media (max-width: 900px) {
  .browse-filter-tool {
    width: min(380px, calc(100vw - 24px));
    min-width: 0;
  }
}

@media (max-width: 700px) {
  .browse-filter-tool--expanded {
    width: 100%;
    height: 100%;
    max-height: 100%;
  }

  .browse-filter-tool:not(.browse-filter-tool--expanded) {
    width: max-content;
    max-width: calc(100vw - 24px);
    max-height: none;
  }

  .filter-panel {
    border-radius: 0;
  }
}

@media (max-width: 560px) {
  .filter-header {
    padding: var(--hs-space-16) var(--hs-space-16) var(--hs-space-10);
  }

  .filter-header h1 {
    font-size: var(--hs-font-md);
  }

  .filter-header-actions {
    gap: var(--hs-space-6);
  }

  .filter-controls,
  .site-list {
    padding-inline: var(--hs-space-16);
  }
}
</style>
