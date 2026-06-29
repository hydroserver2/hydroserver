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
      <span class="filter-chip-count">({{ availableSites.length }})</span>
    </v-btn>

    <v-card v-else class="filter-panel" elevation="10">
      <div class="filter-header">
        <h1>Monitoring sites</h1>

        <div class="filter-header-actions">
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

      <div class="filter-controls">
        <v-text-field
          v-model="siteSearch"
          class="site-search"
          name="browse-site-search"
          label="Search sites"
          :prepend-inner-icon="mdiMagnify"
          clearable
          hide-details
          color="primary"
          autocomplete="off"
          @keydown.enter.prevent="onSiteSearchEnter"
          @click:clear="siteSearch = ''"
        />

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
          color="primary"
          :prepend-inner-icon="mdiBriefcaseOutline"
        >
          <template v-slot:selection="{ item, index }">
            <v-chip
              v-if="index < 2"
              size="small"
              closable
              @click:close="selectedWorkspaces.splice(index, 1)"
            >
              <span>{{ item.title }}</span>
            </v-chip>
            <span
              v-else-if="index === 2"
              class="text-caption text-medium-emphasis ms-1"
            >
              +{{ selectedWorkspaces.length - 2 }} more
            </span>
          </template>
        </v-autocomplete>

        <section v-if="availableSiteTypes.length" class="filter-section">
          <div class="filter-section-title">Site type</div>
          <div class="chip-grid">
            <v-btn
              v-for="siteType in availableSiteTypes"
              :key="siteType"
              class="filter-pill"
              :class="{ selected: selectedSiteTypes.includes(siteType) }"
              :variant="
                selectedSiteTypes.includes(siteType) ? 'tonal' : 'outlined'
              "
              color="default"
              rounded="pill"
              @click="toggleSiteType(siteType)"
            >
              <v-icon
                :icon="getSiteTypeIcon(siteType)"
                :color="
                  selectedSiteTypes.includes(siteType) ? 'primary' : 'default'
                "
                size="16"
              />
              <span>{{ siteType }}</span>
            </v-btn>
          </div>
        </section>
      </div>

      <v-divider />

      <div class="site-list">
        <div class="site-list-count">{{ availableSites.length }} sites</div>

        <div v-if="availableSites.length" class="site-list-items">
          <button
            v-for="site in availableSites"
            :key="site.id"
            type="button"
            class="site-row"
            :class="{ selected: site.id === selectedSiteId }"
            @click="$emit('select-site', site.id)"
          >
            <span class="site-row-icon">
              <v-icon :icon="getSiteTypeIcon(site.siteType)" size="20" />
            </span>

            <span class="site-row-text">
              <span class="site-row-name">{{ site.name }}</span>
              <span class="site-row-workspace">
                {{ getWorkspaceName(site.workspaceId) }}
              </span>
            </span>
          </button>
        </div>

        <div v-else class="empty-sites">No sites match these filters.</div>
      </div>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVocabularyStore } from '@/composables/useVocabulary'
import {
  buildBrowseFilterQuery,
  filterThingMarkers,
  parseBrowseFilterQuery,
} from '@/utils/browseFilters'
import hs, { Workspace } from '@hydroserver/client'
import type { ThingMarker } from '@/types'
import {
  mdiAccessPoint,
  mdiBacteria,
  mdiBeach,
  mdiBiohazard,
  mdiBriefcaseOutline,
  mdiBridge,
  mdiChevronLeft,
  mdiCity,
  mdiCloudArrowDownOutline,
  mdiCloudOutline,
  mdiCounter,
  mdiCrosshairsGps,
  mdiCupWater,
  mdiDatabaseMarkerOutline,
  mdiEarth,
  mdiFactory,
  mdiFerry,
  mdiFilterVariant,
  mdiFilterOffOutline,
  mdiForest,
  mdiFountain,
  mdiGauge,
  mdiGate,
  mdiGreenhouse,
  mdiGrass,
  mdiHomeFlood,
  mdiHydroPower,
  mdiLayersTripleOutline,
  mdiLifebuoy,
  mdiMapMarkerOutline,
  mdiMapMarkerRadiusOutline,
  mdiMagnify,
  mdiMoleculeCo2,
  mdiOfficeBuildingMarkerOutline,
  mdiPipe,
  mdiPipeDisconnected,
  mdiRadar,
  mdiRecycle,
  mdiRoadVariant,
  mdiSatelliteVariant,
  mdiSignCaution,
  mdiSlopeUphill,
  mdiSmog,
  mdiSnowflake,
  mdiSnowflakeMelt,
  mdiSolarPower,
  mdiSpeedometer,
  mdiSprout,
  mdiSprinkler,
  mdiStorageTank,
  mdiTerrain,
  mdiTestTube,
  mdiThermometer,
  mdiThermometerWater,
  mdiTransmissionTower,
  mdiTractor,
  mdiValve,
  mdiWarehouse,
  mdiWaterAlertOutline,
  mdiWaterCheckOutline,
  mdiWaterCircle,
  mdiWaterMinus,
  mdiWaterOutline,
  mdiWaterPercent,
  mdiWaterPlus,
  mdiWater,
  mdiWaterPump,
  mdiWaterWell,
  mdiWeatherCloudy,
  mdiWeatherFog,
  mdiWeatherHazy,
  mdiWeatherPouring,
  mdiWeatherSunny,
  mdiWeatherWindy,
  mdiWaves,
  mdiWavesArrowRight,
  mdiWavesArrowUp,
  mdiVectorPolyline,
} from '@mdi/js'

const vocabularyStore = useVocabularyStore()
const route = useRoute()
const router = useRouter()

const selectedSiteTypes = ref<string[]>([])
const selectedWorkspaces = ref<Workspace[]>([])
const siteSearch = ref('')
const workspaces = ref<Workspace[]>([])
const workspacesLoaded = ref(false)
const isExpanded = ref(true)
const isApplyingRouteState = ref(false)
const hasAppliedInitialRouteState = ref(false)
let routeApplyId = 0

const emit = defineEmits<{
  filter: [ThingMarker[]]
  'select-site': [string | undefined]
}>()

const props = defineProps({
  things: {
    type: Array as () => ThingMarker[],
    required: true,
  },
  thingsLoaded: {
    type: Boolean,
    default: false,
  },
  selectedSiteId: {
    type: String,
    default: undefined,
  },
})

const routeState = parseBrowseFilterQuery(route.query)
if (routeState.drawer !== null) {
  isExpanded.value = routeState.drawer
}

const sortedThings = computed(() =>
  [...props.things].sort((a, b) => a.name.localeCompare(b.name))
)

const workspaceById = computed(
  () => new Map(workspaces.value.map((workspace) => [workspace.id, workspace]))
)

const searchNeedle = computed(() =>
  (siteSearch.value ?? '').trim().toLowerCase()
)

const thingsMatchingSearch = computed(() => {
  if (!searchNeedle.value) return sortedThings.value

  return sortedThings.value.filter((thing) => {
    const workspaceName = getWorkspaceName(thing.workspaceId)
    return [thing.name, workspaceName].some((value) =>
      value.toLowerCase().includes(searchNeedle.value)
    )
  })
})

const availableSites = computed(() =>
  filterThingMarkers(
    thingsMatchingSearch.value,
    selectedWorkspaces.value,
    selectedSiteTypes.value
  )
)

const availableWorkspaces = computed(() => {
  const workspaceIds = new Set(
    filterThingMarkers(
      thingsMatchingSearch.value,
      [],
      selectedSiteTypes.value
    ).map((thing) => thing.workspaceId)
  )

  return workspaces.value.filter((workspace) => workspaceIds.has(workspace.id))
})

const availableSiteTypes = computed(() => {
  const siteTypes = new Set(
    filterThingMarkers(
      thingsMatchingSearch.value,
      selectedWorkspaces.value,
      []
    ).map((thing) => thing.siteType)
  )

  return vocabularyStore.siteTypes.filter((siteType) => siteTypes.has(siteType))
})

const hasActiveFilters = computed(
  () =>
    Boolean((siteSearch.value ?? '').trim()) ||
    selectedWorkspaces.value.length > 0 ||
    selectedSiteTypes.value.length > 0
)

const getWorkspaceName = (workspaceId: string) =>
  workspaceById.value.get(workspaceId)?.name || 'Workspace'

const normalizeSiteType = (siteType: string) =>
  siteType
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ')

const siteTypeIconRules = [
  {
    keywords: ['iot', 'sensor network', 'access point'],
    icon: mdiAccessPoint,
  },
  {
    keywords: [
      'air quality',
      'air monitor',
      'air monitoring',
      'particulate',
      'pm2 5',
      'pm10',
      'smoke',
    ],
    icon: mdiSmog,
  },
  {
    keywords: [
      'bacteria',
      'pathogen',
      'e coli',
      'coliform',
      'habs',
      'hab',
      'algae',
      'cyanobacteria',
      'bloom',
      'algal bloom',
      'harmful algal bloom',
    ],
    icon: mdiBacteria,
  },
  {
    keywords: ['irrigation', 'irrigated'],
    icon: mdiSprinkler,
  },
  {
    keywords: ['coastal', 'beach', 'shore', 'shoreline', 'estuary', 'tidal'],
    icon: mdiBeach,
  },
  {
    keywords: [
      'toxic',
      'contamination',
      'contaminant',
      'hazard',
      'pollution',
      'spill',
    ],
    icon: mdiBiohazard,
  },
  {
    keywords: ['bridge', 'crossing'],
    icon: mdiBridge,
  },
  {
    keywords: [
      'reservoir profile',
      'reservoir profiles',
      'water column profile',
      'depth profile',
    ],
    icon: mdiLayersTripleOutline,
  },
  {
    keywords: ['urban', 'municipal', 'city'],
    icon: mdiCity,
  },
  {
    keywords: ['cloud', 'cloud cover'],
    icon: mdiCloudOutline,
  },
  {
    keywords: ['flow meter', 'flowmeter', 'meter', 'counter', 'totalizer'],
    icon: mdiCounter,
  },
  {
    keywords: ['reference', 'benchmark', 'survey', 'gps'],
    icon: mdiCrosshairsGps,
  },
  {
    keywords: ['drinking water', 'potable'],
    icon: mdiCupWater,
  },
  {
    keywords: ['model', 'grid', 'database'],
    icon: mdiDatabaseMarkerOutline,
  },
  {
    keywords: ['earth', 'environmental', 'ecosystem'],
    icon: mdiEarth,
  },
  {
    keywords: ['industrial', 'industry', 'factory'],
    icon: mdiFactory,
  },
  {
    keywords: ['boat', 'harbor', 'marine'],
    icon: mdiFerry,
  },
  {
    keywords: ['forest', 'riparian', 'watershed'],
    icon: mdiForest,
  },
  {
    keywords: ['spring', 'seep', 'fountain'],
    icon: mdiFountain,
  },
  {
    keywords: ['dry dam release', 'dry dam', 'dam', 'weir', 'sluice'],
    icon: mdiGate,
  },
  {
    keywords: [
      'stream gage',
      'stream gauge',
      'gage',
      'gauge',
      'stage',
      'level',
      'discharge',
      'flow station',
      'flume',
      'stilling well',
    ],
    icon: mdiGauge,
  },
  {
    keywords: ['wetland', 'marsh', 'swamp', 'bog', 'fen'],
    icon: mdiGrass,
  },
  {
    keywords: ['greenhouse'],
    icon: mdiGreenhouse,
  },
  {
    keywords: ['flood', 'floodplain'],
    icon: mdiHomeFlood,
  },
  {
    keywords: ['hydropower', 'hydro power', 'power generation'],
    icon: mdiHydroPower,
  },
  {
    keywords: ['monitoring station', 'station', 'site'],
    icon: mdiMapMarkerRadiusOutline,
  },
  {
    keywords: ['co2', 'carbon dioxide', 'greenhouse gas'],
    icon: mdiMoleculeCo2,
  },
  {
    keywords: ['facility', 'building', 'public works'],
    icon: mdiOfficeBuildingMarkerOutline,
  },
  {
    keywords: ['pipe', 'pipeline', 'conduit'],
    icon: mdiPipe,
  },
  {
    keywords: ['buoy'],
    icon: mdiLifebuoy,
  },
  {
    keywords: ['radar', 'doppler'],
    icon: mdiRadar,
  },
  {
    keywords: [
      'combined sewer',
      'sanitary sewer',
      'wastewater',
      'waste water',
      'effluent',
      'sewer',
      'reclaimed',
      'reuse',
    ],
    icon: mdiRecycle,
  },
  {
    keywords: ['culvert', 'road crossing', 'road'],
    icon: mdiRoadVariant,
  },
  {
    keywords: [
      'channel',
      'conveyance',
      'delivery',
      'route',
      'transfer',
      'distribution',
      'ditch',
      'lateral',
      'canal',
      'aqueduct',
    ],
    icon: mdiVectorPolyline,
  },
  {
    keywords: ['remote sensing', 'satellite'],
    icon: mdiSatelliteVariant,
  },
  {
    keywords: ['warning', 'alert', 'watch'],
    icon: mdiSignCaution,
  },
  {
    keywords: ['slope', 'hillslope'],
    icon: mdiSlopeUphill,
  },
  {
    keywords: ['snow', 'snowpack', 'snotel', 'ice', 'glacier'],
    icon: mdiSnowflake,
  },
  {
    keywords: ['snowmelt', 'snow melt'],
    icon: mdiSnowflakeMelt,
  },
  {
    keywords: ['solar power', 'solar panel'],
    icon: mdiSolarPower,
  },
  {
    keywords: ['pressure', 'speed', 'velocity'],
    icon: mdiSpeedometer,
  },
  {
    keywords: ['soil moisture'],
    icon: mdiSprout,
  },
  {
    keywords: ['soil', 'terrain', 'land'],
    icon: mdiTerrain,
  },
  {
    keywords: ['tank', 'storage tank', 'cistern'],
    icon: mdiStorageTank,
  },
  {
    keywords: [
      'water quality sample',
      'water quality samples',
      'quality sample',
      'grab sample',
      'field sample',
      'chemistry',
      'chemical',
      'sample',
      'sampling',
      'lab',
      'laboratory',
    ],
    icon: mdiTestTube,
  },
  {
    keywords: ['temperature', 'thermal'],
    icon: mdiThermometer,
  },
  {
    keywords: ['water temperature'],
    icon: mdiThermometerWater,
  },
  {
    keywords: ['agricultural', 'agriculture', 'farm', 'crop'],
    icon: mdiTractor,
  },
  {
    keywords: ['telemetry', 'telemetered', 'radio', 'tower'],
    icon: mdiTransmissionTower,
  },
  {
    keywords: ['valve', 'turnout', 'gate valve', 'headgate'],
    icon: mdiValve,
  },
  {
    keywords: ['warehouse', 'storage'],
    icon: mdiWarehouse,
  },
  {
    keywords: ['creek', 'river', 'stream', 'brook', 'tributary'],
    icon: mdiWater,
  },
  {
    keywords: ['drought', 'dry'],
    icon: mdiWaterAlertOutline,
  },
  // TODO: no dedicated treatment-plant icon in MDI 7.4.47; revisit
  {
    keywords: ['water treatment', 'treatment plant', 'treatment works'],
    icon: mdiFilterVariant,
  },
  {
    keywords: [
      'water quality',
      'water quality sensor',
      'quality sensor',
      'sonde',
      'multiparameter',
      'conductivity',
      'dissolved oxygen',
      'turbidity',
      'ph',
      'chlorophyll',
      'nutrient',
      'water check',
      'water status',
      'sediment',
      'suspended sediment',
      'tss',
      'bedload',
    ],
    icon: mdiWaterCheckOutline,
  },
  {
    keywords: ['water supply', 'supply', 'source water'],
    icon: mdiWaterCircle,
  },
  {
    keywords: [
      'withdrawal',
      'intake',
      'diverted',
      'diversion',
      'point of diversion',
    ],
    icon: mdiWaterMinus,
  },
  {
    keywords: ['surface water'],
    icon: mdiWaterOutline,
  },
  {
    keywords: ['humidity', 'moisture', 'dew point'],
    icon: mdiWaterPercent,
  },
  {
    keywords: [
      'injection',
      'recharge',
      'addition',
      'infiltration',
      'managed aquifer recharge',
    ],
    icon: mdiWaterPlus,
  },
  {
    keywords: ['pump station', 'pump', 'pumping', 'lift station'],
    icon: mdiWaterPump,
  },
  {
    keywords: [
      'well',
      'ground water',
      'groundwater',
      'groundwater well',
      'wellfield',
      'aquifer',
      'piezometer',
      'borehole',
    ],
    icon: mdiWaterWell,
  },
  {
    keywords: [
      'reservoir',
      'reservoir lake',
      'lake',
      'pond',
      'pool',
      'impoundment',
    ],
    icon: mdiWaves,
  },
  {
    keywords: ['reservoir release', 'release', 'outflow', 'spillway'],
    icon: mdiWavesArrowRight,
  },
  {
    keywords: [
      'weather station',
      'weather',
      'meteorological',
      'meteorology',
      'met station',
    ],
    icon: mdiWeatherCloudy,
  },
  {
    keywords: ['fog', 'visibility', 'mist'],
    icon: mdiWeatherFog,
  },
  {
    keywords: ['dust', 'smoke haze', 'haze', 'hazy'],
    icon: mdiWeatherHazy,
  },
  // TODO: no drain/storm-sewer icon in MDI 7.4.47; pipe-disconnected is a stand-in
  {
    keywords: [
      'storm sewer',
      'storm drain',
      'stormwater',
      'storm water',
      'drainage',
      'drain',
      'outfall',
    ],
    icon: mdiPipeDisconnected,
  },
  {
    keywords: ['atmospheric deposition', 'atmospheric', 'deposition'],
    icon: mdiCloudArrowDownOutline,
  },
  {
    keywords: ['precipitation', 'precip', 'rain', 'rainfall', 'storm'],
    icon: mdiWeatherPouring,
  },
  {
    keywords: ['solar', 'radiation', 'sun'],
    icon: mdiWeatherSunny,
  },
  {
    keywords: ['evaporation', 'evapotranspiration'],
    icon: mdiWavesArrowUp,
  },
  {
    keywords: ['wind', 'anemometer'],
    icon: mdiWeatherWindy,
  },
]

const matchesSiteTypeKeyword = (normalizedSiteType: string, keyword: string) =>
  ` ${normalizedSiteType} `.includes(` ${normalizeSiteType(keyword)} `)

// Prefer the longest / most specific keyword so multi-word site types resolve
// before generic substrings like "moisture" or "sample".
const getSiteTypeIcon = (siteType: string) => {
  const normalized = normalizeSiteType(siteType)
  return (
    siteTypeIconRules
      .flatMap(({ keywords, icon }) =>
        keywords.map((keyword) => ({ keyword, icon }))
      )
      .filter(({ keyword }) => matchesSiteTypeKeyword(normalized, keyword))
      .sort(
        (a, b) =>
          normalizeSiteType(b.keyword).length -
          normalizeSiteType(a.keyword).length
      )[0]?.icon ??
    mdiMapMarkerOutline
  )
}

const toggleSiteType = (siteType: string) => {
  selectedSiteTypes.value = selectedSiteTypes.value.includes(siteType)
    ? selectedSiteTypes.value.filter((selected) => selected !== siteType)
    : [...selectedSiteTypes.value, siteType]
}

const setExpanded = (value: boolean) => {
  isExpanded.value = value
}

// Let the user quickly jump to a site: typing a query and pressing Enter
// selects the first match while leaving the search field focused and intact.
const onSiteSearchEnter = () => {
  const firstSite = availableSites.value[0]
  if (firstSite) {
    emit('select-site', firstSite.id)
  }
}

const emitFilteredThings = () => {
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
  if (!props.thingsLoaded || !workspacesLoaded.value) return

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
  emitFilteredThings()
  void syncRouteFromSelection(linkedSiteId)
}

const onClearFilters = () => {
  selectedSiteTypes.value = []
  selectedWorkspaces.value = []
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

watch([selectedSiteTypes, selectedWorkspaces, siteSearch], emitFilteredThings, {
  deep: true,
})

watch(
  [selectedSiteTypes, selectedWorkspaces, siteSearch, isExpanded],
  () => syncRouteFromSelection(),
  { deep: true }
)

watch(
  () => props.selectedSiteId,
  (siteId) => syncRouteFromSelection(siteId)
)

watch(
  () =>
    [
      route.query,
      props.things,
      props.thingsLoaded,
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
    if (!props.thingsLoaded) return
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
  (siteType) => siteType,
  (siteType) => siteType
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
  padding-inline: 14px;
  color: #222529;
  box-shadow: 0 4px 16px rgba(22, 27, 34, 0.16) !important;
}

.filter-chip :deep(.v-btn__content) {
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
}

.filter-chip-count {
  color: #8b8f96;
  font-weight: 600;
}

.filter-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px 10px;
}

.filter-header h1 {
  margin: 0;
  color: #202124;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 0;
}

.filter-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.filter-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 20px 14px;
}

.site-search :deep(.v-field),
.workspace-filter :deep(.v-field) {
  border-radius: 8px;
  font-size: 13px;
}

.site-search :deep(.v-field__input),
.workspace-filter :deep(.v-field__input) {
  font-size: 13px;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-section-title {
  color: #5f6368;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-pill {
  min-height: 30px;
  padding-inline: 10px;
  color: #63676d;
  border-color: #dce0e5;
  font-size: 12px;
  font-weight: 600;
}

.filter-pill :deep(.v-btn__content) {
  gap: 6px;
  letter-spacing: 0;
}

.filter-pill.selected {
  color: #1976d2;
  border-color: rgba(33, 150, 243, 0.38);
  background: rgba(33, 150, 243, 0.1);
}

.reset-filters-btn {
  min-width: 0;
  padding-inline: 8px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0;
}

.reset-filters-btn :deep(.v-btn__prepend) {
  margin-inline-end: 4px;
}

.site-list {
  flex: 1;
  min-height: 0;
  overflow: hidden auto;
  padding: 12px 20px 16px;
}

.site-list-count {
  margin-bottom: 10px;
  color: #5f6368;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.site-list-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.site-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 46px;
  padding: 6px 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  text-decoration: none;
}

.site-row:hover,
.site-row.selected {
  background: rgba(33, 150, 243, 0.1);
}

.site-row:hover .site-row-name,
.site-row.selected .site-row-name {
  color: rgb(var(--v-theme-primary));
}

.site-row-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: #f1f3f6;
  color: #5f6368;
}

.site-row-text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.site-row-name,
.site-row-workspace {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-row-name {
  color: #202124;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.25;
}

.site-row-workspace {
  color: #5f6368;
  font-size: 11px;
  font-weight: 500;
}

.empty-sites {
  display: flex;
  min-height: 120px;
  align-items: center;
  justify-content: center;
  color: #8a8d91;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
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
    padding: 16px 16px 10px;
  }

  .filter-header h1 {
    font-size: 17px;
  }

  .filter-header-actions {
    gap: 6px;
  }

  .filter-controls,
  .site-list {
    padding-inline: 16px;
  }
}
</style>
