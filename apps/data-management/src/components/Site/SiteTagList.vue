<template>
  <v-card class="site-tag-list" flat>
    <div class="site-tag-list__header">
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

    <dl v-if="entries.length" class="site-tag-list__items">
      <div
        v-for="[key, value] in entries"
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
    <p v-else class="site-tag-list__empty hs-text-sm text-medium-emphasis">
      No tags yet.
    </p>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Tags } from '@hydroserver/client'

const props = defineProps<{ tags?: Tags | null; canEdit?: boolean }>()
const emit = defineEmits<{ edit: [] }>()

const entries = computed(() =>
  Object.entries(props.tags ?? {}).map(
    ([key, value]) => [key, String(value ?? '')] as const
  )
)

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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--hs-space-10) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
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
