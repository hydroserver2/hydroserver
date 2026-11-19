<template>
  <div
    class="site-photos-panel"
    :class="{ 'site-photos-panel--dragging': isDragging }"
    data-testid="site-photos-panel"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- The tab already shows the photo count, so the toolbar only holds the action. -->
    <div v-if="canEdit && !isManaging" class="site-photos-panel__toolbar">
      <div class="hs-table-actions">
        <v-btn-page-action
          data-testid="manage-site-photos-button"
          @click="startManaging"
        >
          Manage photos
        </v-btn-page-action>
      </div>
    </div>

    <!-- Manage mode: the same photo manager the site form used, inline, with
         Cancel and Save on its "Add photos" heading line. -->
    <section
      v-if="isManaging"
      class="site-photos-panel__manage"
      aria-label="Manage photos"
      data-testid="site-photos-manage"
    >
      <SitePhotoManager :monitoring-site-id="monitoringSiteId">
        <template #actions>
          <div class="hs-table-actions">
            <v-btn-cancel @click="stopManaging">Cancel</v-btn-cancel>
            <v-btn-dialog-action
              :loading="saving"
              data-testid="save-site-photos-button"
              @click="savePhotos"
            >
              Save
            </v-btn-dialog-action>
          </div>
        </template>
      </SitePhotoManager>
    </section>

    <!-- Display mode: photos only. Editors can still drop images anywhere. -->
    <template v-else>
      <v-progress-linear v-if="loading" indeterminate color="primary" />
      <div v-if="photos.length" class="site-photos-panel__grid">
        <button
          v-for="(photo, index) in photos"
          :key="photo.id"
          type="button"
          class="site-photos-panel__tile"
          :aria-label="`Open photo ${index + 1} of ${photos.length}`"
          :data-testid="`site-photo-${index}`"
          @click="emit('open', photo)"
        >
          <v-img :src="photo.link" cover class="h-full w-full" />
        </button>
      </div>
      <p
        v-else-if="!loading"
        class="site-photos-panel__status hs-text-sm text-medium-emphasis"
      >
        No photos added yet.
        <template v-if="acceptsDrops">Drop images here to add them.</template>
      </p>
    </template>

    <div v-if="isDragging" class="site-photos-panel__drop-hint" aria-hidden="true">
      <span class="hs-text-md">Drop photos to add them</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { LinkedResource } from '@hydroserver/client'
import SitePhotoManager from '@/components/Site/SitePhotoManager.vue'
import { usePhotosStore } from '@/store/photos'
import { settings } from '@/config/settings'
import { Snackbar } from '@/utils/notifications'

const props = defineProps<{ monitoringSiteId: string; canEdit?: boolean }>()
const emit = defineEmits<{ open: [photo: LinkedResource] }>()

const photosStore = usePhotosStore()
const { photos, loading, newPhotos } = storeToRefs(photosStore)

const ALLOWED_TYPES = ['image/jpeg', 'image/png']

const isManaging = ref(false)
const saving = ref(false)
const isDragging = ref(false)
// dragenter/dragleave also fire for every child element; count them so the
// hint doesn't flicker while the pointer moves across photos.
let dragDepth = 0

// Dropping uploads straight away in display mode. In manage mode the photo
// manager's own drop area collects files for Save instead.
const acceptsDrops = computed(
  () =>
    !!props.canEdit &&
    !isManaging.value &&
    settings.extensionsConfiguration.fileUploadEnabled
)

function startManaging() {
  photosStore.resetPendingPhotos()
  isManaging.value = true
}

function stopManaging() {
  photosStore.resetPendingPhotos()
  isManaging.value = false
}

async function savePhotos() {
  saving.value = true
  try {
    await photosStore.updatePhotos(props.monitoringSiteId)
  } finally {
    saving.value = false
  }
  isManaging.value = false
}

function onDragEnter(event: DragEvent) {
  if (!acceptsDrops.value || !event.dataTransfer?.types.includes('Files')) return
  dragDepth += 1
  isDragging.value = true
}

function onDragLeave() {
  if (!isDragging.value) return
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) isDragging.value = false
}

async function onDrop(event: DragEvent) {
  dragDepth = 0
  isDragging.value = false
  if (!acceptsDrops.value) return

  const files = Array.from(event.dataTransfer?.files ?? [])
  const images = files.filter((file) => ALLOWED_TYPES.includes(file.type))
  if (images.length < files.length) {
    Snackbar.error('Only JPEG and PNG images can be added.')
  }
  if (!images.length) return

  photosStore.resetPendingPhotos()
  newPhotos.value = images
  await photosStore.updatePhotos(props.monitoringSiteId)
}
</script>

<style scoped>
.site-photos-panel {
  position: relative;
  min-height: 12rem;
}

.site-photos-panel__toolbar {
  display: flex;
  justify-content: flex-end;
  padding: var(--hs-space-12) var(--hs-space-16) 0;
}

.site-photos-panel__manage {
  padding: var(--hs-space-16);
}

.site-photos-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: var(--hs-space-12);
  padding: var(--hs-space-16);
}

.site-photos-panel__tile {
  aspect-ratio: 4 / 3;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
  background: var(--hs-surface-muted);
  cursor: zoom-in;
}

.site-photos-panel__status {
  margin: 0;
  padding: var(--hs-space-16);
  text-align: center;
}

/* Covers the tab while files are dragged over it, like Google Photos. */
.site-photos-panel__drop-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgb(var(--v-theme-primary));
  border-radius: var(--hs-radius-md);
  background: rgb(var(--v-theme-surface) / 0.94);
  color: rgb(var(--v-theme-primary));
  pointer-events: none;
}
</style>
