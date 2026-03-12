<template>
  <h6 class="text-h6 mb-4">Add Photos</h6>
  <v-card-text
    id="drop-area"
    @dragover.prevent
    @drop="handleDrop"
    class="drop-area text-subtitle-2 text-medium-emphasis d-flex mb-6"
  >
    <v-icon :icon="mdiPaperclip" class="mr-1" />
    Drag and drop your photos here, or
    <span @click="triggerFileInput" class="ml-1 add-link">click to upload</span>

    <input
      type="file"
      ref="fileInput"
      id="fileInput"
      multiple
      @change="previewPhotos(($event.target as HTMLInputElement).files)"
      accept="image/jpeg, image/png"
      style="display: none"
    />
  </v-card-text>

  <div class="photo-container">
    <div
      v-if="thingId && photos"
      v-for="photo in photos"
      :key="photo.name"
      class="photo-wrapper"
    >
      <img
        v-if="!photosToDelete.includes(photo.name)"
        :src="photo.link"
        class="photo"
      />
      <v-icon
        v-if="!photosToDelete.includes(photo.name)"
        color="red-darken-1"
        class="delete-icon"
        @click="photosToDelete.push(photo.name)"
        :icon="mdiCloseCircle"
      />
    </div>

    <div
      v-for="(photo, index) in previewedPhotos"
      :key="index"
      class="photo-wrapper"
    >
      <img :src="photo" class="photo" />
      <v-icon
        color="red-darken-1"
        class="delete-icon"
        @click="removePhoto(index)"
        :icon="mdiCloseCircle"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePhotosStore } from '@/store/photos'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import { Snackbar } from '@/utils/notifications'
import { mdiCloseCircle, mdiPaperclip } from '@mdi/js'

const { photos, newPhotos, photosToDelete } = storeToRefs(usePhotosStore())

const props = defineProps({ thingId: String })

const previewedPhotos = ref<string[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

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
