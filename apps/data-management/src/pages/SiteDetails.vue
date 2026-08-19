<template>
  <div v-if="loaded && authorized" class="my-3 mx-4 flex flex-col gap-2">
    <v-row v-if="monitoringSite" class="align-center gap-y-[0.35rem]">
      <v-col
        cols="12"
        class="d-flex align-center flex-wrap justify-space-between gap-2 max-[600px]:flex-col max-[600px]:items-start"
      >
        <h5 class="text-h5 mt-2 mb-0">{{ monitoringSite.name }}</h5>

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
        <v-dialog v-if="monitoringSite" v-model="isRegisterModalOpen" width="80rem">
          <SiteForm
            @close="onSiteFormClosed"
            :monitoring-site-id="monitoringSiteId"
            :workspace-id="monitoringSite.workspaceId"
          />
        </v-dialog>
      </v-col>
    </v-row>

    <v-row v-if="monitoringSite">
      <v-col>
        <div class="w-full">
          <div class="h-88 w-full max-[960px]:h-72">
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
                  <div class="text-subtitle-2 font-weight-medium mb-2">
                    Location
                  </div>
                  <div class="grid gap-1">
                    <div
                      v-for="detail in locationDetails"
                      :key="detail.label"
                      class="flex flex-col"
                    >
                      <span class="text-caption text-medium-emphasis">
                        {{ detail.label }}
                      </span>
                      <span class="text-body-2">{{ detail.value }}</span>
                    </div>
                  </div>
                </v-card>
              </template>
            </OpenLayersMap>
          </div>
          <v-card
            v-if="isMobile"
            class="mt-3 w-full bg-white/95 px-3 py-2"
            elevation="4"
          >
            <div class="text-subtitle-2 font-weight-medium mb-2">Location</div>
            <div class="grid gap-1">
              <div
                v-for="detail in locationDetails"
                :key="detail.label"
                class="flex flex-col"
              >
                <span class="text-caption text-medium-emphasis">
                  {{ detail.label }}
                </span>
                <span class="text-body-2">{{ detail.value }}</span>
              </div>
            </div>
          </v-card>
        </div>
      </v-col>
    </v-row>

    <v-row class="mb-0">
      <v-col cols="12" md="8">
        <SiteDetailsTable :rating-curve-count="ratingCurveCount" />
      </v-col>

      <v-col cols="12" md="4">
        <div class="d-flex align-center justify-space-between mb-2">
          <h5 class="text-h6 mb-0">Site photos</h5>
          <span v-if="hasPhotos" class="text-caption text-medium-emphasis">
            {{ photos?.length }} photos
          </span>
        </div>
        <div
          v-if="hasPhotos"
          class="grid grid-cols-[repeat(auto-fill,minmax(90px,1fr))] gap-2 min-[961px]:grid-cols-[repeat(auto-fit,85px)] min-[961px]:justify-start min-[961px]:max-h-48 min-[961px]:overflow-hidden"
        >
          <button
            v-for="(photo, index) in visiblePhotos"
            :key="photo.name"
            class="relative block aspect-square cursor-pointer appearance-none overflow-hidden rounded-lg border border-black/10 bg-transparent p-0"
            type="button"
            @click="openPhoto(photo)"
          >
            <v-img :src="photo.link" cover class="h-full w-full" />
            <div
              v-if="index === visiblePhotos.length - 1 && extraPhotoCount > 0"
              class="absolute inset-0 flex items-center justify-center bg-black/55 text-base font-semibold text-white"
            >
              +{{ extraPhotoCount }}
            </div>
          </button>
        </div>
        <div v-else-if="loading" class="text-center">
          <p>
            Your photos are being uploaded. They will appear once the upload is
            complete.
          </p>
          <v-progress-circular indeterminate color="primary" />
        </div>
        <div v-else class="text-body-2 text-medium-emphasis">
          No photos added yet.
        </div>
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
          class="text-caption text-medium-emphasis"
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
    <h5 class="text-h5 my-4">
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
  FileAttachment,
} from '@hydroserver/client'
import router from '@/router/router'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import SiteForm from '@/components/Site/SiteForm.vue'
import SiteAccessControl from '@/components/Site/SiteAccessControl.vue'
import DatastreamTable from '@/components/Datastream/DatastreamTable.vue'
import SiteDetailsTable from '@/components/Site/SiteDetailsTable.vue'
import SiteDeleteModal from '@/components/Site/SiteDeleteModal.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
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
      label: 'State/Province',
      value: formatLocationValue(location.adminArea1),
    },
    {
      label: 'County/District',
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
  const res = await hs.monitoringSites.getAttachments(monitoringSiteId)
  if (!res.ok || !Array.isArray(res.data)) return

  photos.value = res.data.filter(
    (attachment: FileAttachment) => attachment.fileAttachmentType === 'Photo'
  )
}

async function loadRatingCurveCount() {
  const items = await hs.ratingCurves.listItemsForMonitoringSite(monitoringSiteId)
  ratingCurveCount.value = items.length
}

function onSiteFormClosed() {
  isRegisterModalOpen.value = false
  void loadMonitoringSitePhotos()
  void loadRatingCurveCount()
}

function openPhoto(photo: FileAttachment) {
  const index = photos.value?.findIndex((p) => p.name === photo.name) ?? -1
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
