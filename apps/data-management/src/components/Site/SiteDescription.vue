<template>
  <div class="site-description" :class="{ 'site-description--expanded': expanded }">
    <p
      :id="textId"
      ref="textEl"
      class="site-description__text hs-text-sm"
      data-testid="site-description-text"
    >
      {{ text || 'No description provided.' }}
    </p>
    <!-- Only offered when the text is longer than three lines. Same text
         button style as the card's other links (View all, Edit tags). -->
    <div v-if="isOverflowing || expanded" class="site-description__actions">
      <v-btn
        variant="text"
        size="small"
        color="primary"
        :aria-expanded="expanded"
        :aria-controls="textId"
        data-testid="site-description-toggle"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'View less' : 'View more' }}
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'

const props = defineProps<{ text?: string | null }>()

const textId = useId()
const textEl = ref<HTMLElement | null>(null)
const expanded = ref(false)
const isOverflowing = ref(false)
let resizeObserver: ResizeObserver | undefined

// Collapsed, CSS clamps the text to three lines; it overflows when its full
// height is taller than that.
function measure() {
  const el = textEl.value
  if (!el || expanded.value) return
  isOverflowing.value = el.scrollHeight > el.clientHeight + 1
}

onMounted(() => {
  measure()
  if (typeof ResizeObserver !== 'undefined' && textEl.value) {
    resizeObserver = new ResizeObserver(measure)
    resizeObserver.observe(textEl.value)
  }
})

onBeforeUnmount(() => resizeObserver?.disconnect())

watch(
  () => props.text,
  async () => {
    expanded.value = false
    await nextTick()
    measure()
  }
)
</script>

<style scoped>
.site-description {
  padding: var(--hs-space-12) var(--hs-space-16);
}

/* Three full lines ending in an ellipsis when there's more. */
.site-description__text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  margin: 0;
  overflow: hidden;
  white-space: pre-line;
  overflow-wrap: anywhere;
}

.site-description--expanded .site-description__text {
  display: block;
  -webkit-line-clamp: unset;
  line-clamp: none;
}

.site-description__actions {
  display: flex;
  justify-content: flex-end;
  margin: var(--hs-space-4) calc(-1 * var(--hs-space-8)) calc(-1 * var(--hs-space-4)) 0;
}
</style>
