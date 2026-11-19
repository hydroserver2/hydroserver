<template>
  <div v-if="loaded && authorized" class="site-details-page">
    <v-row
      v-if="monitoringSite"
      class="site-details-header align-center gap-y-[0.35rem]"
    >
      <v-col
        cols="12"
        class="d-flex align-center flex-wrap justify-space-between gap-2 max-[600px]:flex-col max-[600px]:items-start"
      >
        <h1 class="site-details-title hs-heading ma-0">{{ monitoringSite.name }}</h1>

        <div
          class="flex items-center flex-wrap gap-2 max-[600px]:w-full max-[600px]:flex-col max-[600px]:items-stretch"
        >
          <HydroShareArchivalButton v-if="canEditMonitoringSite && hydroShareConnected" />

          <v-btn
            v-if="canEditMonitoringSite"
            variant="outlined"
            data-testid="site-access-control-button"
            @click="isAccessControlModalOpen = true"
          >
            Access control
          </v-btn>

          <v-btn
            v-if="canEditMonitoringSite"
            variant="outlined"
            color="secondary"
            data-testid="edit-site-button"
            @click="isRegisterModalOpen = true"
          >
            Edit site information
          </v-btn>

          <v-menu v-if="canEditMonitoringSite" location="bottom end">
            <template #activator="{ props: menuProps }">
              <v-btn
                v-bind="menuProps"
                color="primary"
                :prepend-icon="mdiCloudUploadOutline"
                :append-icon="mdiChevronDown"
                data-testid="stream-data-button"
              >
                Stream data
              </v-btn>
            </template>
            <v-list density="comfortable">
              <v-list-item
                :to="orchestrationIngestionRoute"
                :prepend-icon="mdiCogSyncOutline"
                title="Automated job orchestration"
                subtitle="Schedule recurring imports from a data connection"
              />
              <v-list-item
                :to="{ name: 'StreamingDataLoaderDownload' }"
                :prepend-icon="mdiDownloadBoxOutline"
                title="Streaming Data Loader"
                subtitle="Desktop app that streams local CSV files as they update"
              />
              <v-list-item
                :href="pythonClientGuideUrl"
                target="_blank"
                rel="noopener noreferrer"
                :prepend-icon="mdiLanguagePython"
                title="API via scripts"
                subtitle="Push observations with hydroserverpy or the REST API"
              />
            </v-list>
          </v-menu>

          <v-btn
            v-if="
              hasPermission(PermissionResource.MonitoringSite, PermissionAction.Delete)
            "
            color="red-darken-3"
            data-testid="delete-site-button"
            @click="isDeleteModalOpen = true"
          >
            Delete site
          </v-btn>
        </div>

        <v-dialog v-model="isDeleteModalOpen" v-if="monitoringSite" width="40rem">
          <SiteDeleteModal
            :monitoringSite="monitoringSite"
            @switch-to-access-control="switchToAccessControlModal"
            @close="isDeleteModalOpen = false"
            @delete="onDeleteMonitoringSite"
          />
        </v-dialog>
        <v-dialog v-model="isAccessControlModalOpen" width="40rem">
          <SiteAccessControl
            @close="isAccessControlModalOpen = false"
            :monitoring-site-id="monitoringSiteId"
          />
        </v-dialog>
        <v-dialog v-model="isRegisterModalOpen" width="80rem">
          <SiteForm
            v-if="monitoringSite && isRegisterModalOpen"
            @close="onSiteFormClosed"
            :monitoring-site-id="monitoringSiteId"
            :workspace-id="monitoringSite.workspaceId"
          />
        </v-dialog>
      </v-col>
    </v-row>

    <div class="site-details-body">
      <div v-if="monitoringSite" class="site-details-layout">
        <aside class="site-details-aside" aria-label="About this site">
          <SitePhotoCarousel
            :photos="photos ?? []"
            @open="openPhoto"
            @view-all="activeTab = 'photos'"
          />

          <v-card class="site-details-card" flat>
            <h2 class="site-details-card__title hs-text-md">Site information</h2>
            <dl class="site-details-facts hs-text-sm" data-testid="site-facts">
              <div class="site-details-facts__row site-details-facts__row--stacked">
                <dt>Site UUID</dt>
                <dd class="site-details-facts__uuid">
                  <span class="hs-font-data">{{ monitoringSite.id }}</span>
                  <HsCopyButton
                    :value="monitoringSite.id"
                    :label="monitoringSite.name"
                    data-testid="copy-site-id"
                    @copied="Snackbar.success('Site UUID copied to clipboard')"
                    @error="Snackbar.error('Failed to copy site UUID')"
                  />
                </dd>
              </div>
              <div v-if="monitoringSite.code" class="site-details-facts__row">
                <dt>Site code</dt>
                <dd class="hs-font-data">{{ monitoringSite.code }}</dd>
              </div>
              <div v-if="monitoringSite.type" class="site-details-facts__row">
                <dt>Site type</dt>
                <dd>{{ monitoringSite.type }}</dd>
              </div>
              <div class="site-details-facts__row">
                <dt>Privacy</dt>
                <dd>
                  <v-chip
                    size="small"
                    variant="tonal"
                    :color="monitoringSite.isPrivate ? 'error' : 'success'"
                    :prepend-icon="
                      monitoringSite.isPrivate ? mdiLock : mdiLockOpenVariant
                    "
                    data-testid="site-privacy-chip"
                  >
                    {{ monitoringSite.isPrivate ? 'Private' : 'Public' }}
                  </v-chip>
                </dd>
              </div>
            </dl>
            <p class="site-details-card__body hs-text-sm">
              {{ monitoringSite.description || 'No description provided.' }}
            </p>
          </v-card>

          <SiteTagList
            :tags="monitoringSite.tags"
            :can-edit="canEditMonitoringSite"
            @edit="isRegisterModalOpen = true"
          />
        </aside>

        <section class="site-details-map" aria-label="Site location">
          <div class="h-80 w-full max-[960px]:h-72">
            <OpenLayersMap
              :monitoringSites="[monitoringSite]"
              startInSatellite
              class="h-full w-full"
            >
              <template #overlay>
                <v-card
                  v-if="!isMobile"
                  class="mb-2 ml-2 max-w-[18rem] bg-white/95 px-3 py-2"
                  elevation="4"
                >
                  <div class="hs-text-sm font-weight-medium mb-2">Location</div>
                  <div class="grid gap-1">
                    <div
                      v-for="detail in locationDetails"
                      :key="detail.label"
                      class="flex flex-col"
                    >
                      <span class="hs-text-2xs text-medium-emphasis">
                        {{ detail.label }}
                      </span>
                      <span class="hs-text-sm">{{ detail.value }}</span>
                    </div>
                  </div>
                </v-card>
              </template>
            </OpenLayersMap>
          </div>
          <div v-if="isMobile" class="px-3 py-2">
            <div class="hs-text-sm font-weight-medium mb-2">Location</div>
            <div class="grid gap-1">
              <div
                v-for="detail in locationDetails"
                :key="detail.label"
                class="flex flex-col"
              >
                <span class="hs-text-2xs text-medium-emphasis">
                  {{ detail.label }}
                </span>
                <span class="hs-text-sm">{{ detail.value }}</span>
              </div>
            </div>
          </div>
        </section>

        <v-card class="site-details-tabs" flat>
          <v-tabs
            v-model="activeTab"
            color="primary"
            density="comfortable"
            show-arrows
            class="site-details-tabs__bar"
          >
            <v-tab value="datastreams" data-testid="site-tab-datastreams">
              Datastreams
              <v-chip
                v-if="datastreamCount !== null"
                size="x-small"
                variant="tonal"
                class="ml-2"
              >
                {{ datastreamCount }}
              </v-chip>
            </v-tab>
            <v-tab value="photos" data-testid="site-tab-photos">
              Photos
              <v-chip size="x-small" variant="tonal" class="ml-2">
                {{ photos?.length ?? 0 }}
              </v-chip>
            </v-tab>
            <v-tab value="rating-curves" data-testid="site-tab-rating-curves">
              Rating curves
              <v-chip size="x-small" variant="tonal" class="ml-2">
                {{ ratingCurveCount }}
              </v-chip>
            </v-tab>
          </v-tabs>

          <v-window v-model="activeTab" :touch="false">
            <v-window-item
              value="datastreams"
              :transition="false"
              :reverse-transition="false"
            >
              <div class="site-details-tabs__panel">
                <DatastreamTable
                  v-if="workspace"
                  :workspace="workspace"
                  :target-datastream-id="targetDatastreamId"
                  @datastream-count="datastreamCount = $event"
                />
              </div>
            </v-window-item>
            <v-window-item
              value="photos"
              :transition="false"
              :reverse-transition="false"
            >
              <SitePhotosPanel
                :monitoring-site-id="monitoringSiteId"
                :can-edit="canEditMonitoringSite"
                @open="openPhoto"
              />
            </v-window-item>
            <v-window-item
              value="rating-curves"
              :transition="false"
              :reverse-transition="false"
            >
              <div class="site-details-tabs__panel">
                <RatingCurveTable
                  :monitoring-site-id="monitoringSiteId"
                  :workspace-id="monitoringSite.workspaceId"
                  :can-edit="canEditMonitoringSite"
                  @rating-curves-changed="ratingCurveCount = $event.length"
                />
              </div>
            </v-window-item>
          </v-window>
        </v-card>
      </div>
    </div>

    <v-dialog v-model="isPhotoViewerOpen" width="60rem">
      <v-card v-if="selectedPhoto">
        <div
          class="flex h-[32rem] w-full items-center justify-center bg-slate-900/90 max-[960px]:h-[24rem] max-[600px]:h-[18rem]"
        >
          <v-img :src="selectedPhoto.link" contain class="h-full w-full" />
        </div>
        <v-card-text
          v-if="selectedPhoto.name"
          class="hs-text-2xs text-medium-emphasis"
        >
          {{ selectedPhoto.name }}
        </v-card-text>
        <v-card-actions
          class="flex flex-wrap items-center justify-center gap-2 px-4 pb-3 pt-1"
        >
          <v-btn
            variant="outlined"
            :prepend-icon="mdiChevronLeft"
            :disabled="!hasMultiplePhotos"
            @click="showPrevPhoto"
          >
            Previous
          </v-btn>
          <v-btn
            variant="outlined"
            :append-icon="mdiChevronRight"
            :disabled="!hasMultiplePhotos"
            @click="showNextPhoto"
          >
            Next
          </v-btn>
          <v-spacer />
          <v-btn variant="text" @click="isPhotoViewerOpen = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
  <v-container v-else-if="loaded && !authorized">
    <h5 class="hs-text-md my-4">
      You are not authorized to view this private site.
    </h5>
  </v-container>
  <FullScreenLoader v-else />
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePhotosStore } from '@/store/photos'
import { useMonitoringSiteStore } from '@/store/monitoringSite'
import { useTagStore } from '@/store/tags'
import { storeToRefs } from 'pinia'
import hs, {
  PermissionAction,
  PermissionResource,
  Workspace,
  LinkedResource,
} from '@hydroserver/client'
import router from '@/router/router'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import SiteForm from '@/components/Site/SiteForm.vue'
import SiteAccessControl from '@/components/Site/SiteAccessControl.vue'
import DatastreamTable from '@/components/Datastream/DatastreamTable.vue'
import SiteDeleteModal from '@/components/Site/SiteDeleteModal.vue'
import SitePhotoCarousel from '@/components/Site/SitePhotoCarousel.vue'
import SitePhotosPanel from '@/components/Site/SitePhotosPanel.vue'
import SiteTagList from '@/components/Site/SiteTagList.vue'
import RatingCurveTable from '@/components/Orchestration/data-products/RatingCurveTable.vue'
import {
  HsCopyButton,
  HsFullScreenLoader as FullScreenLoader,
} from '@hydroserver/design-system/vue'
import { Snackbar } from '@/utils/notifications'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useHydroShare } from '@/composables/useHydroShare'
import { useHydroShareStore } from '@/store/hydroShare'
import HydroShareArchivalButton from '@/components/HydroShare/HydroShareArchivalButton.vue'
import {
  mdiChevronLeft,
  mdiChevronRight,
  mdiDownloadBoxOutline,
  mdiCloudUploadOutline,
  mdiChevronDown,
  mdiCogSyncOutline,
  mdiLanguagePython,
  mdiLock,
  mdiLockOpenVariant,
} from '@mdi/js'
import { useDisplay } from 'vuetify/lib/framework.mjs'

const pythonClientGuideUrl =
  'https://hydroserver2.github.io/hydroserver/user-guides/how-to/using-the-python-client.html'

const route = useRoute()
const monitoringSiteId = route.params.id.toString()
const targetDatastreamId = computed(() => {
  const param = route.query.datastream
  return Array.isArray(param) ? param[0] ?? '' : `${param ?? ''}`
})

const siteTabs = ['datastreams', 'photos', 'rating-curves'] as const
type SiteTab = (typeof siteTabs)[number]

// The selected tab lives in the URL (?tab=photos) so views can be linked and
// the back button works. A ?datastream= deep link always opens Datastreams.
const activeTab = computed<SiteTab>({
  get() {
    if (targetDatastreamId.value) return 'datastreams'
    const param = route.query.tab
    const value = Array.isArray(param) ? param[0] : param
    return siteTabs.includes(value as SiteTab) ? (value as SiteTab) : 'datastreams'
  },
  set(tab) {
    const { tab: _currentTab, datastream: _datastream, ...query } = route.query
    void router.replace({
      query: tab === 'datastreams' ? query : { ...query, tab },
    })
  },
})
const orchestrationIngestionRoute = computed(() => ({
  name: 'OrchestrationView',
  params: { view: 'ingestion' },
  query: {
    workspace_id: monitoringSite.value?.workspaceId,
    site_id: monitoringSiteId,
  },
}))
const { photos } = storeToRefs(usePhotosStore())
const workspace = ref<Workspace>()

const { isConnectionEnabled: hydroShareEnabled, isConnected: hydroShareConnected } =
  useHydroShare()
const { hydroShareArchive } = storeToRefs(useHydroShareStore())

const { hasPermission } = useWorkspacePermissions(workspace)
const loaded = ref(false)
const authorized = ref(true)
const { monitoringSite } = storeToRefs(useMonitoringSiteStore())
const { tags } = storeToRefs(useTagStore())
const { xs } = useDisplay()
const isMobile = computed(() => xs.value)
const canEditMonitoringSite = computed(() =>
  hasPermission(PermissionResource.MonitoringSite, PermissionAction.Edit)
)

const isRegisterModalOpen = ref(false)
const isDeleteModalOpen = ref(false)
const isAccessControlModalOpen = ref(false)
const ratingCurveCount = ref(0)
// Fetched on load so the tab chip shows on every tab; DatastreamTable keeps it
// current as datastreams are added or removed. null hides the chip until known.
const datastreamCount = ref<number | null>(null)
const selectedPhotoIndex = ref<number | null>(null)
const isPhotoViewerOpen = ref(false)
const hasMultiplePhotos = computed(() => (photos.value?.length ?? 0) > 1)
const selectedPhoto = computed(() => {
  if (selectedPhotoIndex.value === null) return null
  return photos.value?.[selectedPhotoIndex.value] ?? null
})

const locationDetails = computed(() => {
  const location = monitoringSite.value
  if (!location) return []

  return [
    {
      label: 'Latitude',
      value: formatCoordinate(location.latitude),
    },
    {
      label: 'Longitude',
      value: formatCoordinate(location.longitude),
    },
    {
      label: 'State/province',
      value: formatLocationValue(location.adminArea1),
    },
    {
      label: 'County/district',
      value: formatLocationValue(location.adminArea2),
    },
    {
      label: 'Country',
      value: formatLocationValue(location.country),
    },
  ]
})

function switchToAccessControlModal() {
  isDeleteModalOpen.value = false
  isAccessControlModalOpen.value = true
}

async function loadMonitoringSitePhotos() {
  const res = await hs.monitoringSites.getLinkedResources(monitoringSiteId)
  if (!res.ok || !Array.isArray(res.data)) return

  photos.value = res.data.filter(
    (linkedResource: LinkedResource) => linkedResource.type === 'Photo'
  )
}

async function loadRatingCurveCount() {
  const items = await hs.ratingCurves.listItemsForMonitoringSite(monitoringSiteId)
  ratingCurveCount.value = items.length
}

// limit=0 asks only for the total (meta.numberMatched), not the rows.
async function loadDatastreamCount() {
  const res = await hs.datastreams.list({
    monitoringSiteId: [monitoringSiteId],
    limit: 0,
  })
  const count = res.ok ? res.meta?.numberMatched : undefined
  // The table may have reported first; its count is just as current.
  if (typeof count === 'number' && datastreamCount.value === null) {
    datastreamCount.value = count
  }
}

function onSiteFormClosed() {
  isRegisterModalOpen.value = false
}

function openPhoto(photo: LinkedResource) {
  const index = photos.value?.findIndex((p) => p.id === photo.id) ?? -1
  if (index < 0) return
  selectedPhotoIndex.value = index
  isPhotoViewerOpen.value = true
}

function showPrevPhoto() {
  if (!photos.value?.length || selectedPhotoIndex.value === null) return
  const total = photos.value.length
  selectedPhotoIndex.value = (selectedPhotoIndex.value - 1 + total) % total
}

function showNextPhoto() {
  if (!photos.value?.length || selectedPhotoIndex.value === null) return
  const total = photos.value.length
  selectedPhotoIndex.value = (selectedPhotoIndex.value + 1) % total
}

function formatCoordinate(value?: number | string | null) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'number') return value.toFixed(6)
  return value.toString()
}

function formatLocationValue(value?: string | number | null) {
  if (value === null || value === undefined || value === '') return '-'
  return value.toString()
}

async function onDeleteMonitoringSite() {
  try {
    await hs.monitoringSites.delete(monitoringSiteId)
    await router.push('/browse')
  } catch (error) {
    console.error('Error deleting monitoringSite', error)
  }
}

onMounted(async () => {
  photos.value = []
  void loadMonitoringSitePhotos().catch((error) =>
    console.error('Error fetching photos from DB', error)
  )
  void loadRatingCurveCount().catch((error) =>
    console.error('Error fetching rating curves from DB', error)
  )
  void loadDatastreamCount().catch((error) =>
    console.error('Error fetching datastream count', error)
  )

  const monitoringSiteResponse = await hs.monitoringSites
    .getItem(monitoringSiteId)
    .catch((error: any) => {
      if (parseInt(error.status) === 403) authorized.value = false
      else console.error('Error fetching monitoringSite', error)

      return null
    })

  tags.value = monitoringSiteResponse?.tags ?? {}
  monitoringSite.value = monitoringSiteResponse ?? undefined
  try {
    workspace.value =
      (await hs.workspaces.getItem(monitoringSite.value!.workspaceId)) ?? undefined
  } catch (error) {
    console.error('Error fetching workspace', error)
  }
  hydroShareArchive.value = null
  loaded.value = true
})
</script>

<style scoped>
/* Like Workspaces and Job Orchestration: the page fills the space under the
   navbar and only the body scrolls, so the navbar and title stay full width
   above the scroll bar. */
.site-details-page {
  --site-details-page-gutter: var(--hs-space-24);
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  overflow: hidden;
}

.site-details-header {
  /* .v-row defaults to flex: 1 1 auto, which would split the height with the body. */
  flex: 0 0 auto;
  margin: 0;
  padding: var(--hs-space-16) var(--site-details-page-gutter);
  background: var(--hs-surface);
  border-bottom: 1px solid var(--hs-border);
}

.site-details-header > .v-col {
  padding: 0;
}

.site-details-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

/* Basis 0 so the stacked phone header (flex-direction: column) doesn't turn
   the basis into a fixed height; min-width makes the buttons wrap on desktop. */
.site-details-title {
  flex: 1 1 0%;
  min-width: min(100%, 20rem);
  overflow-wrap: anywhere;
}

/* Phone and tablet: map, then site context, then the tabs. */
.site-details-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    'map'
    'aside'
    'tabs';
  gap: var(--hs-space-16);
  margin: var(--hs-space-16) var(--site-details-page-gutter);
}

/* Desktop: site context column on the left, map above the tabs on the right. */
@media (min-width: 960px) {
  .site-details-layout {
    grid-template-columns: minmax(18rem, 22rem) minmax(0, 1fr);
    grid-template-rows: auto 1fr;
    grid-template-areas:
      'aside map'
      'aside tabs';
    gap: var(--hs-space-16) var(--hs-space-24);
  }
}

.site-details-aside {
  grid-area: aside;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-16);
  min-width: 0;
}

.site-details-map {
  grid-area: map;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
}

.site-details-tabs {
  grid-area: tabs;
  align-self: start;
  min-width: 0;
  border: 1px solid var(--hs-border);
}

.site-details-tabs__bar {
  border-bottom: 1px solid var(--hs-border);
}

.site-details-tabs__panel {
  padding: var(--hs-space-16);
}

.site-details-card {
  border: 1px solid var(--hs-border);
}

.site-details-card__title {
  margin: 0;
  padding: var(--hs-space-10) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
}

.site-details-card__body {
  margin: 0;
  padding: var(--hs-space-12) var(--hs-space-16);
  white-space: pre-line;
}

/* Label/value rows; the UUID gets its own full-width line so it never wraps. */
.site-details-facts {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: var(--hs-space-8) var(--hs-space-16);
  margin: 0;
  padding: var(--hs-space-12) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
}

.site-details-facts__row {
  display: contents;
}

.site-details-facts__row dt {
  color: var(--hs-text-secondary);
}

.site-details-facts__row dd {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

.site-details-facts__row--stacked dt,
.site-details-facts__row--stacked dd {
  grid-column: 1 / -1;
}

.site-details-facts__row--stacked dd {
  margin-top: calc(-1 * var(--hs-space-8));
}

.site-details-facts__uuid {
  display: flex;
  align-items: center;
  gap: var(--hs-space-4);
}

/* Phones keep normal page scrolling: a pinned header would take too much of
   the small screen. */
@media (max-width: 700px) {
  .site-details-page {
    --site-details-page-gutter: var(--hs-space-16);
    height: auto;
    overflow: visible;
  }

  .site-details-header {
    padding-block: var(--hs-space-12);
  }

  .site-details-body {
    overflow: visible;
  }
}
</style>
