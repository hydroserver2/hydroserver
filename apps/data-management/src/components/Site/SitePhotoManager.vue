<template>
  <h6 class="text-h6 mb-4">Add Photos</h6>

  <v-btn-toggle
    v-if="fileUploadEnabled"
    v-model="addMode"
    mandatory
    density="compact"
    color="primary"
    variant="outlined"
    rounded="xl"
    divided
    class="mb-4"
  >
    <v-btn value="upload">Upload files</v-btn>
    <v-btn value="link">Add link</v-btn>
  </v-btn-toggle>

  <v-card-text
    v-if="fileUploadEnabled && addMode === 'upload'"
    id="drop-area"
    @dragover.prevent
    @drop="handleDrop"
    class="drop-area text-subtitle-2 text-medium-emphasis d-flex mb-6"
    data-testid="site-photo-drop-area"
  >
    <v-icon :icon="mdiPaperclip" class="mr-1" />
    Drag and drop your photos here, or
    <span @click="triggerFileInput" class="ml-1 add-link">click to upload</span>

    <input
      type="file"
      ref="fileInput"
      id="fileInput"
      multiple
      data-testid="site-photo-input"
      @change="previewPhotos(($event.target as HTMLInputElement).files)"
      accept="image/jpeg, image/png"
      style="display: none"
    />
  </v-card-text>

  <v-row
    v-if="!fileUploadEnabled || addMode === 'link'"
    align="center"
    class="mb-6"
  >
    <v-col cols="9">
      <v-text-field
        v-model="newLinkInput"
        label="Photo URL"
        density="comfortable"
        hide-details
        data-testid="site-photo-link-input"
        @keyup.enter="addLink"
      />
    </v-col>
    <v-col>
      <v-btn
        :disabled="!newLinkInput.trim()"
        @click="addLink"
        data-testid="site-photo-link-add"
        >Add</v-btn
      >
    </v-col>
  </v-row>

  <div class="photo-container">
    <div
      v-if="monitoringSiteId && photos"
      v-for="(photo, index) in photos"
      :key="photo.id"
      class="photo-wrapper"
      :data-testid="`site-photo-existing-${index}`"
    >
      <img
        v-if="!photosToDelete.includes(photo.id)"
        :src="photo.link"
        class="photo"
      />
      <v-icon
        v-if="!photosToDelete.includes(photo.id)"
        color="red-darken-1"
        class="delete-icon"
        @click="photosToDelete.push(photo.id)"
        :icon="mdiCloseCircle"
        :data-testid="`delete-existing-photo-${index}`"
      />
    </div>

    <div
      v-for="(photo, index) in previewedPhotos"
      :key="index"
      class="photo-wrapper"
      :data-testid="`site-photo-preview-${index}`"
    >
      <img :src="photo" class="photo" />
      <v-icon
        color="red-darken-1"
        class="delete-icon"
        @click="removePhoto(index)"
        :icon="mdiCloseCircle"
        :data-testid="`delete-preview-photo-${index}`"
      />
    </div>

    <div
      v-for="(link, index) in newLinks"
      :key="`link-${index}`"
      class="photo-wrapper"
      :data-testid="`site-photo-link-preview-${index}`"
    >
      <img :src="link" class="photo" />
      <v-icon
        color="red-darken-1"
        class="delete-icon"
        @click="newLinks.splice(index, 1)"
        :icon="mdiCloseCircle"
        :data-testid="`delete-link-preview-${index}`"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePhotosStore } from '@/store/photos'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import { Snackbar } from '@/utils/notifications'
import { settings } from '@/config/settings'
import { mdiCloseCircle, mdiPaperclip } from '@mdi/js'

const { photos, newPhotos, newLinks, photosToDelete } = storeToRefs(
  usePhotosStore()
)

const props = defineProps({ monitoringSiteId: String })

const fileUploadEnabled = settings.extensionsConfiguration.fileUploadEnabled

const previewedPhotos = ref<string[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const addMode = ref<'upload' | 'link'>('upload')
const newLinkInput = ref('')

function handleDrop(e: DragEvent) {
  e.preventDefault()
  let files = e.dataTransfer?.files
  if (files) {
    let filteredFiles = Array.from(files).filter(
      (file) => file.type === 'image/jpeg' || file.type === 'image/png'
    )
    if (filteredFiles.length > 0) {
      previewPhotos(filteredFiles)
    } else {
      Snackbar.error('only JPEG and PNG images are allowed')
    }
  }
}

function previewPhotos(files: File[] | FileList | null) {
  if (!files) return

  Array.from(files).forEach((photo) => {
    let reader = new FileReader()
    reader.onload = (e) => {
      if ((e.target as FileReader).result) {
        previewedPhotos.value.push((e.target as FileReader).result as string)
        newPhotos.value.push(photo)
      }
    }
    reader.readAsDataURL(photo)
  })
}

function triggerFileInput() {
  if (fileInput.value) fileInput.value.click()
}

function removePhoto(index: number) {
  previewedPhotos.value.splice(index, 1)
  newPhotos.value.splice(index, 1)
}

function addLink() {
  const value = newLinkInput.value.trim()
  if (!value) return
  newLinks.value.push(value)
  newLinkInput.value = ''
}
</script>

<style scoped lang="scss">
.drop-area {
  border: 2px dashed #ccc;
}

.add-link {
  color: blue;
  text-decoration: underline;
  cursor: pointer;
}

.photo-container {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
}

.photo-wrapper {
  position: relative;
  margin-right: 20px;
  width: 6rem;
  margin-bottom: 20px;
}

.photo {
  width: 100px;
  height: 100px;
  object-fit: cover;
}

.delete-icon {
  position: absolute;
  top: -20px;
  right: -20px;
}
</style>
