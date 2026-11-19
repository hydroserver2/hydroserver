<template>
  <v-card v-if="photos.length" class="site-photo-carousel" flat>
    <div class="site-photo-carousel__header">
      <h2 class="hs-text-md mb-0">Photos</h2>
      <v-btn
        variant="text"
        size="small"
        color="primary"
        data-testid="site-photo-carousel-view-all"
        @click="emit('view-all')"
      >
        View all {{ photos.length }}
      </v-btn>
    </div>

    <div class="site-photo-carousel__frame">
      <button
        type="button"
        class="site-photo-carousel__image-button"
        :aria-label="`Open photo ${currentIndex + 1} of ${photos.length}`"
        @click="emit('open', currentPhoto)"
      >
        <v-img :src="currentPhoto.link" cover class="h-full w-full" />
      </button>
      <template v-if="photos.length > 1">
        <v-btn-icon
          class="site-photo-carousel__nav site-photo-carousel__nav--prev"
          :icon="mdiChevronLeft"
          aria-label="Previous photo"
          @click="showPrevious"
        />
        <v-btn-icon
          class="site-photo-carousel__nav site-photo-carousel__nav--next"
          :icon="mdiChevronRight"
          aria-label="Next photo"
          @click="showNext"
        />
      </template>
    </div>

    <div class="site-photo-carousel__caption hs-text-sm">
      <span class="site-photo-carousel__name">{{ currentPhoto.name }}</span>
      <span class="text-medium-emphasis flex-shrink-0">
        {{ currentIndex + 1 }} of {{ photos.length }}
      </span>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { LinkedResource } from '@hydroserver/client'
import { mdiChevronLeft, mdiChevronRight } from '@mdi/js'

const props = defineProps<{ photos: LinkedResource[] }>()
const emit = defineEmits<{
  open: [photo: LinkedResource]
  'view-all': []
}>()

const currentIndex = ref(0)
const currentPhoto = computed(() => props.photos[currentIndex.value])

watch(
  () => props.photos.length,
  (length) => {
    if (currentIndex.value >= length) currentIndex.value = 0
  }
)

function showPrevious() {
  const total = props.photos.length
  currentIndex.value = (currentIndex.value - 1 + total) % total
}

function showNext() {
  currentIndex.value = (currentIndex.value + 1) % props.photos.length
}
</script>

<style scoped>
.site-photo-carousel {
  border: 1px solid var(--hs-border);
  overflow: hidden;
}

.site-photo-carousel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--hs-space-10) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
}

.site-photo-carousel__frame {
  position: relative;
  height: 15rem;
  background: var(--hs-surface-muted);
}

.site-photo-carousel__image-button {
  display: block;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
}

.site-photo-carousel__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: var(--hs-surface);
  box-shadow: var(--hs-shadow-popover);
}

.site-photo-carousel__nav--prev {
  left: var(--hs-space-8);
}

.site-photo-carousel__nav--next {
  right: var(--hs-space-8);
}

.site-photo-carousel__caption {
  display: flex;
  justify-content: space-between;
  gap: var(--hs-space-8);
  padding: var(--hs-space-8) var(--hs-space-16);
}

.site-photo-carousel__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
