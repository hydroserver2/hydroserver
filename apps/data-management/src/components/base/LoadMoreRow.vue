<template>
  <tbody>
    <tr ref="row" class="load-more-row">
      <td :colspan="colspan">
        <div v-if="error" class="load-more-row__status hs-text-sm">
          {{ error }}
          <v-btn size="small" variant="text" @click="$emit('retry')">
            Retry
          </v-btn>
        </div>
        <v-progress-linear
          v-else-if="loading"
          indeterminate
          color="primary"
          aria-label="Loading more rows"
        />
      </td>
    </tr>
  </tbody>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

// Place in a table's `#tbody` slot. Requests the next page whenever this row
// is scrolled into view (or is still visible after the last page loaded).
const props = defineProps<{
  colspan: number
  hasMore: boolean
  loading: boolean
  error?: string
}>()
const emit = defineEmits<{ load: []; retry: [] }>()

const row = ref<HTMLElement>()
let observer: IntersectionObserver | undefined

onMounted(() => {
  observer = new IntersectionObserver(
    ([entry]) => {
      if (
        entry.isIntersecting &&
        props.hasMore &&
        !props.loading &&
        !props.error
      )
        emit('load')
    },
    { root: row.value?.closest('.v-table__wrapper'), rootMargin: '200px' }
  )
  if (row.value) observer.observe(row.value)
})
onBeforeUnmount(() => observer?.disconnect())

// Re-observing reports fresh visibility once the new rows have rendered, so a
// short page still fills the view without racing ahead of the layout.
watch(
  () => props.loading,
  (loading) => {
    if (loading || !row.value) return
    observer?.unobserve(row.value)
    observer?.observe(row.value)
  },
  { flush: 'post' }
)
</script>

<style scoped>
.load-more-row td {
  height: auto !important;
  padding: 0 !important;
  border: 0 !important;
}
.load-more-row__status {
  display: flex;
  gap: var(--hs-space-8);
  align-items: center;
  justify-content: center;
  padding: var(--hs-space-8);
  color: var(--hs-text-secondary);
}
</style>
