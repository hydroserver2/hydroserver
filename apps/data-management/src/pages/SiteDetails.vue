<template>
  <div v-if="loaded && authorized" class="my-3 mx-4 flex flex-col gap-2">
    <v-row v-if="thing" class="align-center gap-y-[0.35rem]">
      <v-col
        cols="12"
        class="d-flex align-center flex-wrap justify-between gap-2 max-[600px]:flex-col max-[600px]:items-start"
      >
        <h5 class="text-h5 mt-2 mb-0">{{ thing.name }}</h5>
        <div
          class="flex items-center gap-2 ml-auto max-[600px]:w-full max-[600px]:ml-0"
        >
          <v-btn
            v-if="
              hasPermission(PermissionResource.Thing, PermissionAction.Delete)
            "
            class="max-[600px]:self-start"
            color="red-darken-3"
            @click="isDeleteModalOpen = true"
          >
            Delete site
          </v-btn>
          <div class="flex-1" />
          <HydroShareArchivalButton
            v-if="
              hasPermission(PermissionResource.Thing, PermissionAction.Edit) &&
              hydroShareConnected
            "
          />
        </div>
        <v-dialog v-model="isDeleteModalOpen" v-if="thing" width="40rem">
          <SiteDeleteModal
            :thing="thing"
            @switch-to-access-control="switchToAccessControlModal"
            @close="isDeleteModalOpen = false"
            @delete="onDeleteThing"
          />
        </v-dialog>
      </v-col>
    </v-row>

    <v-row v-if="thing">
      <v-col>
        <div class="w-full">
          <div class="h-88 w-full max-[960px]:h-72">
            <OpenLayersMap
              :things="[thing]"
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

    <v-row class="align-center mb-2">
      <v-col
        cols="12"
        md="8"
        class="d-flex align-center flex-wrap gap-2 max-[600px]:flex-col max-[600px]:items-start"
      >
        <h5 class="text-h6 mb-0 max-[600px]:w-full">Site information</h5>

        <v-btn
          v-if="hasPermission(PermissionResource.Thing, PermissionAction.Edit)"
          class="max-[600px]:self-start"
          @click="isAccessControlModalOpen = true"
        >
          Access control
        </v-btn>
        <v-dialog v-model="isAccessControlModalOpen" width="40rem">
          <SiteAccessControl
            @close="isAccessControlModalOpen = false"
            :thing-id="thingId"
          />
        </v-dialog>

        <v-btn
          v-if="
            hasPermission(PermissionResource.Thing, PermissionAction.Edit) &&
            !!thing
          "
          class="max-[600px]:self-start"
          @click="isRegisterModalOpen = true"
          color="secondary"
        >
          Edit site information
        </v-btn>
        <v-dialog v-if="thing" v-model="isRegisterModalOpen" width="80rem">
          <SiteForm
            @close="onSiteFormClosed"
            :thing-id="thingId"
            :workspace-id="thing.workspaceId"
          />
        </v-dialog>
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

    <DatastreamTable v-if="thing && workspace" :workspace="workspace" />

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
import { useThingStore } from '@/store/thing'
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
import { mdiChevronLeft, mdiChevronRight } from '@mdi/js'
import { useDisplay } from 'vuetify/lib/framework.mjs'

const thingId = useRoute().params.id.toString()
const { photos, loading } = storeToRefs(usePhotosStore())
const workspace = ref<Workspace>()

const { isConnected: hydroShareConnected } = useHydroShare()
const { hydroShareArchive } = storeToRefs(useHydroShareStore())

const { hasPermission } = useWorkspacePermissions(workspace)
const loaded = ref(false)
const authorized = ref(true)
const { thing } = storeToRefs(useThingStore())
const { tags } = storeToRefs(useTagStore())
const { xs } = useDisplay()
const isMobile = computed(() => xs.value)
const canEditThing = computed(() =>
  hasPermission(PermissionResource.Thing, PermissionAction.Edit)
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
  const location = thing.value?.location
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

async function loadThingPhotos() {
  const res = await hs.things.getAttachments(thingId)
  if (!res.ok || !Array.isArray(res.data)) return

  ratingCurveCount.value = res.data.filter(
    (attachment: FileAttachment) =>
      attachment.fileAttachmentType === 'rating_curve'
  ).length
  photos.value = res.data.filter(
    (attachment: FileAttachment) => attachment.fileAttachmentType === 'Photo'
  )
}

function onSiteFormClosed() {
  isRegisterModalOpen.value = false
  void loadThingPhotos()
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

async function onDeleteThing() {
  try {
    await hs.things.delete(thingId)
    await router.push('/sites')
  } catch (error) {
    console.error('Error deleting thing', error)
  }
}

onMounted(async () => {
  photos.value = []
  void loadThingPhotos().catch((error) =>
    console.error('Error fetching photos from DB', error)
  )

  const [thingResponse, tagResponse] = await Promise.all([
    hs.things.getItem(thingId).catch((error: any) => {
      if (parseInt(error.status) === 403) authorized.value = false
      else console.error('Error fetching thing', error)

      return null
    }),
    hs.things.getTags(thingId).catch((error) => {
      console.error('Error fetching additional metadata tags', error)
      return null
    }),
  ])

  tags.value = tagResponse?.data
  thing.value = thingResponse ?? undefined
  try {
    workspace.value =
      (await hs.workspaces.getItem(thing.value!.workspaceId)) ?? undefined
  } catch (error) {
    console.error('Error fetching workspace', error)
  }
  hydroShareArchive.value = null
  loaded.value = true
})
</script>
