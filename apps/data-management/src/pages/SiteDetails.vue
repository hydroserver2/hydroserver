<template>
  <div v-if="loaded && authorized" class="my-3 mx-4 flex flex-col gap-2">
    <v-row v-if="monitoringSite" class="align-center gap-y-[0.35rem]">
      <v-col
        cols="12"
        class="d-flex align-center flex-wrap justify-space-between gap-2 max-[600px]:flex-col max-[600px]:items-start"
      >
        <div class="mt-2">
          <h5 class="hs-text-md mb-0">{{ monitoringSite.name }}</h5>
          <div
            v-if="siteSummary.length || ratingCurveCount"
            class="hs-text-sm text-medium-emphasis mt-1 flex flex-wrap items-center gap-x-1"
          >
            <span v-if="siteSummary.length">{{ siteSummary.join(' • ') }}</span>
            <span
              v-if="siteSummary.length && ratingCurveCount"
              aria-hidden="true"
            >
              •
            </span>
            <v-btn
              v-if="ratingCurveCount"
              class="site-rating-curve-link"
              variant="text"
              color="teal-darken-1"
              @click="siteDetailsTable?.openRatingCurveDialog()"
            >
              View rating curves ({{ ratingCurveCount }})
            </v-btn>
          </div>
        </div>

        <div
          class="flex items-center flex-wrap gap-2 max-[600px]:w-full max-[600px]:flex-col max-[600px]:items-stretch"
        >
          <HydroShareArchivalButton
            v-if="canEditMonitoringSite && hydroShareConnected"
          />

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
              hasPermission(
                PermissionResource.MonitoringSite,
                PermissionAction.Delete
              )
            "
            color="red-darken-3"
            data-testid="delete-site-button"
            @click="isDeleteModalOpen = true"
          >
            Delete site
          </v-btn>
        </div>

        <v-dialog
          v-model="isDeleteModalOpen"
          v-if="monitoringSite"
          width="40rem"
        >
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
        <v-dialog
          v-if="monitoringSite"
          v-model="isRegisterModalOpen"
          width="80rem"
        >
          <SiteForm
            @close="onSiteFormClosed"
            :monitoring-site-id="monitoringSiteId"
            :workspace-id="monitoringSite.workspaceId"
          />
        </v-dialog>
      </v-col>
    </v-row>

    <v-row v-if="monitoringSite" class="site-details-layout mb-0">
      <v-col cols="12" md="8" class="site-details-main">
        <p v-if="monitoringSite.description" class="site-description">
          {{ monitoringSite.description }}
        </p>

        <v-divider v-if="monitoringSite.description" class="my-4" />

        <template v-if="metadataEntries.length">
          <div class="site-metadata-list">
            <v-chip
              v-for="[key, value] in visibleMetadataEntries"
              :key="key"
              rounded="true"
              color="primary"
              variant="tonal"
            >
              <span class="site-metadata-key">{{ key }}:</span>
              <span class="ms-1">
                <a
                  v-if="isUrl(value)"
                  :href="value"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ value }}
                </a>
                <span v-else>{{ value }}</span>
              </span>
            </v-chip>
          </div>
          <v-pagination
            v-if="metadataPageCount > 1"
            v-model="metadataPage"
            class="site-metadata-pagination"
            :length="metadataPageCount"
            :total-visible="5"
            density="compact"
            size="small"
          />
        </template>

        <div class="d-flex align-center justify-space-between mt-6 mb-2">
          <h5 class="hs-text-md mb-0">Site photos</h5>
          <span v-if="hasPhotos" class="hs-text-2xs text-medium-emphasis">
            {{ photos?.length }} photos
          </span>
        </div>
        <div class="mb-2">
          <div v-if="hasPhotos" class="flex w-full gap-2 overflow-x-auto">
            <button
              v-for="(photo, index) in visiblePhotos"
              :key="photo.id"
              class="relative block aspect-square w-24 shrink-0 cursor-pointer appearance-none overflow-hidden rounded-lg border border-black/10 bg-transparent p-0"
              type="button"
              @click="openPhoto(photo)"
            >
              <v-img :src="photo.link" cover class="h-full w-full" />
              <div
                v-if="index === visiblePhotos.length - 1 && extraPhotoCount > 0"
                class="absolute inset-0 flex items-center justify-center bg-black/55 hs-subheading text-white"
              >
                +{{ extraPhotoCount }}
              </div>
            </button>
          </div>
          <div v-else-if="loading" class="text-center">
            <p>
              Your photos are being uploaded. They will appear once the upload
              is complete.
            </p>
            <v-progress-circular indeterminate color="primary" />
          </div>
          <div v-else class="text-medium-emphasis">
            <small>No photos added yet.</small>
          </div>
        </div>
      </v-col>

      <v-col cols="12" md="4" class="site-details-sidebar">
        <div class="h-52 w-full">
          <OpenLayersMap
            :monitoringSites="[monitoringSite]"
            startInSatellite
            class="h-full w-full"
          />
        </div>

        <div class="site-location-summary mt-4">{{ locationLine }}</div>

        <dl class="site-identity-list mt-4">
          <div>
            <dt>Site ID</dt>
            <dd>
              <span class="hs-font-data" :title="monitoringSite.id">
                {{ monitoringSite.id }}
              </span>
              <v-btn-icon
                size="small"
                density="comfortable"
                :icon="mdiContentCopy"
                aria-label="Copy site ID"
                @click="copyValue(monitoringSite.id, 'Site ID')"
              />
            </dd>
          </div>
        </dl>

        <SiteDetailsTable ref="siteDetailsTable" dialog-only />
      </v-col>
    </v-row>

    <DatastreamTable
      v-if="monitoringSite && workspace"
      :workspace="workspace"
      :target-datastream-id="targetDatastreamId"
    />

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
import { onMounted, computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { usePhotosStore } from '@/store/photos'
import { useMonitoringSiteStore } from '@/store/monitoringSite'
import { useTagStore } from '@/store/tags'
import { storeToRefs } from 'pinia'
import { Snackbar } from '@/utils/notifications'
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
import SiteDetailsTable from '@/components/Site/SiteDetailsTable.vue'
import SiteDeleteModal from '@/components/Site/SiteDeleteModal.vue'
import { HsFullScreenLoader as FullScreenLoader } from '@hydroserver/design-system/vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useHydroShare } from '@/composables/useHydroShare'
import { useHydroShareStore } from '@/store/hydroShare'
import HydroShareArchivalButton from '@/components/HydroShare/HydroShareArchivalButton.vue'
import { useDisplay } from 'vuetify/lib/framework.mjs'
import {
  mdiChevronLeft,
  mdiChevronRight,
  mdiDownloadBoxOutline,
  mdiCloudUploadOutline,
  mdiChevronDown,
  mdiCogSyncOutline,
  mdiContentCopy,
  mdiLanguagePython,
} from '@mdi/js'

const pythonClientGuideUrl =
  'https://hydroserver2.github.io/hydroserver/user-guides/how-to/using-the-python-client.html'

const route = useRoute()
const monitoringSiteId = route.params.id.toString()
const targetDatastreamId = computed(() => {
  const param = route.query.datastream
  return Array.isArray(param) ? (param[0] ?? '') : `${param ?? ''}`
})
const orchestrationIngestionRoute = computed(() => ({
  name: 'OrchestrationView',
  params: { view: 'ingestion' },
  query: {
    workspace_id: monitoringSite.value?.workspaceId,
    site_id: monitoringSiteId,
  },
}))
const { photos, loading } = storeToRefs(usePhotosStore())
const workspace = ref<Workspace>()

const {
  isConnectionEnabled: hydroShareEnabled,
  isConnected: hydroShareConnected,
} = useHydroShare()
const { hydroShareArchive } = storeToRefs(useHydroShareStore())

const { hasPermission } = useWorkspacePermissions(workspace)
const loaded = ref(false)
const authorized = ref(true)
const { monitoringSite } = storeToRefs(useMonitoringSiteStore())
const { tags } = storeToRefs(useTagStore())
const { width } = useDisplay()
const canEditMonitoringSite = computed(() =>
  hasPermission(PermissionResource.MonitoringSite, PermissionAction.Edit)
)
const siteSummary = computed(() =>
  [
    monitoringSite.value?.code,
    monitoringSite.value?.type,
    monitoringSite.value?.isPrivate ? 'Private' : 'Public',
  ].filter((value): value is string => Boolean(value))
)
const metadataEntries = computed(() =>
  Object.entries(tags.value).sort(([firstKey], [secondKey]) =>
    firstKey.localeCompare(secondKey)
  )
)
const metadataPage = ref(1)
const metadataColumns = computed(() => {
  if (width.value >= 1600) return 4
  if (width.value >= 960) return 3
  if (width.value >= 600) return 2
  return 1
})
const metadataPageSize = computed(() => metadataColumns.value * 4)
const metadataPageCount = computed(() =>
  Math.ceil(metadataEntries.value.length / metadataPageSize.value)
)
const visibleMetadataEntries = computed(() => {
  const first = (metadataPage.value - 1) * metadataPageSize.value
  return metadataEntries.value.slice(first, first + metadataPageSize.value)
})
watch(metadataPageCount, (pageCount) => {
  metadataPage.value = Math.min(metadataPage.value, Math.max(pageCount, 1))
})
const locationLine = computed(() => {
  const site = monitoringSite.value
  if (!site) return ''

  const place = [site.adminArea2, site.adminArea1, site.country]
    .filter((value): value is string => Boolean(value))
    .join(', ')

  return [
    `Lat: ${formatCoordinate(site.latitude)}`,
    `Lon: ${formatCoordinate(site.longitude)}`,
    place,
  ]
    .filter(Boolean)
    .join(' • ')
})

const hasPhotos = computed(() => !loading.value && photos.value?.length > 0)
const maxPhotoThumbnails = 6
const visiblePhotos = computed(() =>
  photos.value ? photos.value.slice(0, maxPhotoThumbnails) : []
)
const extraPhotoCount = computed(() =>
  Math.max(0, (photos.value?.length ?? 0) - maxPhotoThumbnails)
)

const isRegisterModalOpen = ref(false)
const isDeleteModalOpen = ref(false)
const isAccessControlModalOpen = ref(false)
const ratingCurveCount = ref(0)
const siteDetailsTable = ref<InstanceType<typeof SiteDetailsTable> | null>(null)
const selectedPhotoIndex = ref<number | null>(null)
const isPhotoViewerOpen = ref(false)
const hasMultiplePhotos = computed(() => (photos.value?.length ?? 0) > 1)
const selectedPhoto = computed(() => {
  if (selectedPhotoIndex.value === null) return null
  return photos.value?.[selectedPhotoIndex.value] ?? null
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
  const items =
    await hs.ratingCurves.listItemsForMonitoringSite(monitoringSiteId)
  ratingCurveCount.value = items.length
}

function onSiteFormClosed() {
  isRegisterModalOpen.value = false
  void loadMonitoringSitePhotos()
  void loadRatingCurveCount()
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

function isUrl(value: string): boolean {
  try {
    new URL(value)
    return true
  } catch {
    return false
  }
}

async function copyValue(value: string, label: string) {
  try {
    await navigator.clipboard.writeText(value)
    Snackbar.success(`${label} copied to clipboard`)
  } catch {
    Snackbar.error(`Failed to copy ${label.toLowerCase()}`)
  }
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
      (await hs.workspaces.getItem(monitoringSite.value!.workspaceId)) ??
      undefined
  } catch (error) {
    console.error('Error fetching workspace', error)
  }
  hydroShareArchive.value = null
  loaded.value = true
})
</script>

<style scoped>
.site-rating-curve-link {
  min-height: 0;
  height: auto;
  padding: 0;
  font-size: inherit;
  line-height: inherit;
  text-transform: none;
}

.site-description {
  max-width: 54rem;
  margin: 0;
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-medium);
  line-height: 1.5;
}

.site-metadata-list {
  display: flex;
  height: calc(var(--hs-space-32) * 4);
  flex-wrap: wrap;
  align-content: flex-start;
  gap: var(--hs-space-6);
  overflow: hidden;
}

.site-metadata-key {
  font-weight: var(--hs-font-weight-semibold);
}

.site-metadata-pagination {
  justify-content: flex-start;
  margin-top: var(--hs-space-2);
}

.site-location-summary {
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-semibold);
}

.site-identity-list dd {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--hs-space-4);
}

.site-identity-list dd > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-identity-list {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-12);
  margin-bottom: 0;
}

.site-identity-list dt {
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-medium);
}

.site-identity-list dd {
  margin: var(--hs-space-2) 0 0;
  font-size: var(--hs-font-sm);
}

@media (min-width: 960px) {
  .site-details-sidebar {
    border-left: 1px solid var(--hs-border);
    padding-left: var(--hs-space-32);
  }
}
</style>
