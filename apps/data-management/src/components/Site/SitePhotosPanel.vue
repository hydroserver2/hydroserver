<template>
  <div class="site-photos-panel">
    <div class="site-photos-panel__toolbar">
      <span class="hs-text-sm text-medium-emphasis">
        {{ photos.length }} {{ photos.length === 1 ? 'photo' : 'photos' }}
      </span>
      <v-btn-page-action
        v-if="canEdit"
        size="small"
        data-testid="manage-site-photos-button"
        @click="openManageDialog"
      >
        Manage photos
      </v-btn-page-action>
    </div>

    <div v-if="loading" class="site-photos-panel__status">
      <p class="hs-text-sm mb-2">
        Your photos are being uploaded. They will appear once the upload is
        complete.
      </p>
      <v-progress-circular indeterminate color="primary" />
    </div>
    <div v-else-if="photos.length" class="site-photos-panel__grid">
      <button
        v-for="(photo, index) in photos"
        :key="photo.id"
        type="button"
        class="site-photos-panel__tile"
        :aria-label="`Open photo ${index + 1} of ${photos.length}`"
        @click="emit('open', photo)"
      >
        <v-img :src="photo.link" cover class="h-full w-full" />
      </button>
    </div>
    <p v-else class="site-photos-panel__status hs-text-sm text-medium-emphasis">
      No photos added yet.
    </p>

    <v-dialog v-model="isManageDialogOpen" width="48rem">
      <v-card>
        <v-card-title class="hs-subheading">Manage photos</v-card-title>
        <v-card-text>
          <SitePhotoManager :monitoring-site-id="monitoringSiteId" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn-cancel @click="closeManageDialog">Cancel</v-btn-cancel>
          <v-btn-dialog-action :loading="saving" @click="savePhotos">
            Save
          </v-btn-dialog-action>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { LinkedResource } from '@hydroserver/client'
import SitePhotoManager from '@/components/Site/SitePhotoManager.vue'
import { usePhotosStore } from '@/store/photos'

const props = defineProps<{ monitoringSiteId: string; canEdit?: boolean }>()
const emit = defineEmits<{ open: [photo: LinkedResource] }>()

const photosStore = usePhotosStore()
const { photos, loading } = storeToRefs(photosStore)

const isManageDialogOpen = ref(false)
const saving = ref(false)

function openManageDialog() {
  photosStore.resetPendingPhotos()
  isManageDialogOpen.value = true
}

function closeManageDialog() {
  isManageDialogOpen.value = false
}

async function savePhotos() {
  saving.value = true
  try {
    await photosStore.updatePhotos(props.monitoringSiteId)
  } finally {
    saving.value = false
  }
  isManageDialogOpen.value = false
}

// Closing the dialog any way other than Save throws away the pending changes.
watch(isManageDialogOpen, (isOpen) => {
  if (!isOpen && !saving.value) photosStore.resetPendingPhotos()
})
</script>

<style scoped>
.site-photos-panel__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--hs-space-12);
  padding: var(--hs-space-12) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
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
</style>
