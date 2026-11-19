<template>
  <v-card class="site-tag-list" flat>
    <div class="site-tag-list__header">
      <div class="site-tag-list__title-row">
        <h2 class="hs-text-md mb-0">Tags</h2>
        <v-btn
          v-if="canEdit"
          variant="text"
          size="small"
          color="primary"
          data-testid="edit-site-tags-button"
          @click="emit('edit')"
        >
          Edit tags
        </v-btn>
      </div>

      <div v-if="showFilter" class="site-tag-list__filter">
        <HsSearchInput
          v-model="query"
          placeholder="Filter tags"
          aria-label="Filter tags by key or value"
          data-testid="site-tag-filter"
        />
        <p
          v-if="query.trim()"
          class="site-tag-list__match-count hs-text-2xs text-medium-emphasis"
          aria-live="polite"
        >
          {{ filteredEntries.length }} of {{ entries.length }} tags
        </p>
      </div>
    </div>

    <dl v-if="filteredEntries.length" class="site-tag-list__items">
      <div
        v-for="[key, value] in filteredEntries"
        :key="key"
        class="site-tag-list__item"
        :data-testid="`site-tag-${key}`"
      >
        <dt class="site-tag-list__key hs-font-data hs-text-2xs">{{ key }}</dt>
        <dd class="site-tag-list__value hs-text-sm">
          <a v-if="isUrl(value)" :href="value" target="_blank" rel="noopener">
            {{ value }}
          </a>
          <template v-else>{{ value }}</template>
        </dd>
      </div>
    </dl>
    <p
      v-else-if="entries.length"
      class="site-tag-list__empty hs-text-sm text-medium-emphasis"
    >
      No tags match “{{ query.trim() }}”.
    </p>
    <p v-else class="site-tag-list__empty hs-text-sm text-medium-emphasis">
      No tags yet.
    </p>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Tags } from '@hydroserver/client'
import { HsSearchInput } from '@hydroserver/design-system/vue'

// A handful of tags is easy to scan; past this, show a filter box.
const FILTER_THRESHOLD = 6

const props = defineProps<{ tags?: Tags | null; canEdit?: boolean }>()
const emit = defineEmits<{ edit: [] }>()

const query = ref('')

// Alphabetical by key, ignoring case; numbers sort naturally (HUC2 < HUC10).
const entries = computed(() =>
  Object.entries(props.tags ?? {})
    .map(([key, value]) => [key, String(value ?? '')] as const)
    .sort(([a], [b]) =>
      a.localeCompare(b, undefined, { sensitivity: 'base', numeric: true })
    )
)

const showFilter = computed(() => entries.value.length > FILTER_THRESHOLD)

// Matches the key or the value, ignoring case.
const filteredEntries = computed(() => {
  const needle = query.value.trim().toLowerCase()
  if (!needle) return entries.value
  return entries.value.filter(
    ([key, value]) =>
      key.toLowerCase().includes(needle) || value.toLowerCase().includes(needle)
  )
})

function isUrl(value: string) {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}
</script>

<style scoped>
.site-tag-list {
  border: 1px solid var(--hs-border);
}

.site-tag-list__header {
  padding: var(--hs-space-10) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
}

.site-tag-list__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.site-tag-list__filter {
  padding: var(--hs-space-8) 0 var(--hs-space-2);
}

.site-tag-list__match-count {
  margin: var(--hs-space-6) 0 0;
}

.site-tag-list__items {
  margin: 0;
}

.site-tag-list__item {
  padding: var(--hs-space-10) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
}

.site-tag-list__item:last-child {
  border-bottom: 0;
}

.site-tag-list__key {
  display: inline-block;
  padding: 0 var(--hs-space-6);
  border-radius: var(--hs-radius-sm);
  background: var(--hs-surface-muted);
  color: var(--hs-primary);
}

.site-tag-list__value {
  margin: var(--hs-space-4) 0 0;
  overflow-wrap: anywhere;
}

.site-tag-list__empty {
  margin: 0;
  padding: var(--hs-space-12) var(--hs-space-16);
}
</style>
