<template>
  <section
    class="hs-table"
    :class="{ 'hs-table--sticky': stickyHeader }"
    :aria-labelledby="titleId"
    :aria-busy="loading || undefined"
  >
    <div class="hs-table__tools">
      <div class="hs-table__heading-row">
        <div class="hs-table__heading">
          <h2 :id="titleId" class="hs-subheading">{{ title }}</h2>
          <span v-if="count !== undefined" class="hs-table__count hs-text-sm">
            {{ count.toLocaleString() }} available
          </span>
        </div>
        <div v-if="$slots.actions" class="hs-table-actions">
          <slot name="actions" />
        </div>
      </div>

      <div v-if="$slots.search" class="hs-table__search">
        <slot name="search" />
      </div>
    </div>

    <div class="hs-table-card hs-table__frame">
      <table class="hs-table__table hs-text-sm">
        <caption v-if="caption" class="hs-table__caption">
          {{
            caption
          }}
        </caption>
        <thead v-if="hasHeader">
          <tr v-if="selectionCount > 0">
            <th :colspan="columnCount" class="hs-table__selection-header">
              <div class="hs-table__header-content">
                <label class="hs-table__selection-summary">
                  <input
                    type="checkbox"
                    class="hs-table__checkbox"
                    :indeterminate="true"
                    aria-label="Clear selected rows"
                    @change="emit('clear-selection')"
                  />
                  <span>{{ selectionLabel }}</span>
                </label>
                <div
                  v-if="$slots['selection-actions']"
                  class="hs-table-actions"
                >
                  <slot name="selection-actions" />
                </div>
              </div>
            </th>
          </tr>
          <tr v-else-if="$slots.filters">
            <th :colspan="columnCount" class="hs-table__filter-header">
              <div class="hs-table__header-content">
                <slot name="filters" />
              </div>
            </th>
          </tr>
          <tr v-if="$slots.head">
            <slot name="head" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading || empty">
            <td :colspan="columnCount" class="hs-table__status">
              <slot v-if="loading" name="loading">
                Loading {{ title.toLowerCase() }}…
              </slot>
              <slot v-else name="empty">{{ emptyMessage }}</slot>
            </td>
          </tr>
          <slot v-else />
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, useId, useSlots } from 'vue'

defineOptions({ name: 'HsTable' })

const props = withDefaults(
  defineProps<{
    title: string
    columnCount: number
    count?: number
    caption?: string
    selectionCount?: number
    selectionLimit?: number
    loading?: boolean
    empty?: boolean
    emptyMessage?: string
    stickyHeader?: boolean
  }>(),
  {
    count: undefined,
    caption: '',
    selectionCount: 0,
    selectionLimit: undefined,
    loading: false,
    empty: false,
    emptyMessage: 'Nothing to show.',
    stickyHeader: true,
  }
)

const emit = defineEmits<{
  'clear-selection': []
}>()

const slots = useSlots()
const titleId = `hs-table-${useId()}`
const hasHeader = computed(
  () => props.selectionCount > 0 || Boolean(slots.filters || slots.head)
)
const selectionLabel = computed(() =>
  props.selectionLimit
    ? `${props.selectionCount} of ${props.selectionLimit} selected`
    : `${props.selectionCount} selected`
)
</script>

<style scoped>
.hs-table {
  display: flex;
  flex: 1;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  min-height: 0;
}

.hs-table__tools {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-10);
  margin-bottom: var(--hs-space-10);
}

.hs-table__heading-row,
.hs-table__heading,
.hs-table__header-content,
.hs-table__selection-summary {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
}

.hs-table__heading-row,
.hs-table__header-content {
  justify-content: space-between;
}

.hs-table__heading {
  gap: var(--hs-space-8);
  align-items: baseline;
}

.hs-table__heading h2 {
  margin: 0;
  color: var(--hs-text-primary);
}

.hs-table__count {
  color: var(--hs-text-secondary);
  white-space: nowrap;
}

.hs-table__search,
.hs-table__search :deep(.hs-search),
.hs-table__search :deep(.hs-query-search) {
  width: 100%;
  max-width: none;
}

.hs-table__frame {
  flex: 0 1 auto;
  max-height: 100%;
  min-height: 0;
  overflow: auto;
}

.hs-table__table {
  width: 100%;
  min-width: 100%;
  border-collapse: collapse;
}

.hs-table--sticky .hs-table__table thead {
  position: sticky;
  top: 0;
  z-index: 2;
}

.hs-table__table :deep(thead th) {
  height: 48px;
  padding: var(--hs-space-8) var(--hs-space-12);
  color: var(--hs-text-secondary);
  font-weight: var(--hs-font-weight-regular);
  text-align: left;
  background: var(--hs-surface-muted);
}

.hs-table__table :deep(thead tr),
.hs-table__table :deep(tbody tr) {
  border-bottom: 1px solid var(--hs-border);
}

.hs-table__table :deep(tbody tr:hover) {
  background: var(--hs-surface-muted);
}

.hs-table__table :deep(tbody td) {
  padding: var(--hs-space-12);
  color: var(--hs-text-primary);
  vertical-align: top;
}

.hs-table__filter-header,
.hs-table__selection-header {
  height: auto !important;
  padding: var(--hs-space-12) !important;
}

.hs-table__selection-header {
  color: var(--hs-text-primary) !important;
  font-weight: var(--hs-font-weight-semibold) !important;
}

.hs-table__checkbox {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}

.hs-table__status {
  padding: var(--hs-space-24) !important;
  color: var(--hs-text-secondary) !important;
  text-align: center;
}

.hs-table__caption {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 600px) {
  .hs-table__heading-row,
  .hs-table__header-content {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
