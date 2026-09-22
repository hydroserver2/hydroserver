<template>
  <v-skeleton-loader
    v-if="loading"
    type="table"
    class="metadata-table-loading-skeleton"
  />
  <v-data-table-virtual
    v-else
    class="metadata-items"
    :headers="headers"
    :items="filteredItems"
    :sort-by="[{ key: titleKey, order: 'asc' }]"
    fixed-header
  >
    <template #[`item.${titleKey}`]="{ item }">
      <HsTableSummary :title="itemTitle(item)" :details="summaryDetails(item)">
        <template #details>
          <li v-for="(detail, index) in summaryDetails(item)" :key="index">
            {{ detail }}
          </li>
          <li v-if="showScope" class="metadata-items__scope">
            <MetadataScopeChip :scope="itemScope(item)" />
          </li>
        </template>
        <template #action>
          <HsCopyButton
            :value="item.id"
            :label="itemTitle(item)"
            :data-testid="`copy-metadata-id-${item.id}`"
            @copied="Snackbar.success('Metadata UUID copied to clipboard')"
            @error="Snackbar.error('Failed to copy metadata UUID')"
          />
        </template>
      </HsTableSummary>
    </template>
    <template #item.actions="{ item }">
      <div class="metadata-items__actions">
        <v-btn
          variant="text"
          size="small"
          color="primary"
          :append-icon="mdiChevronRight"
          :aria-label="`View details for ${itemTitle(item)}`"
          :data-testid="`view-metadata-${item.id}`"
          @click="selectedId = item.id"
          >View details</v-btn
        >
        <slot name="actions" :item="item" />
      </div>
    </template>
  </v-data-table-virtual>

  <v-dialog
    :model-value="!!selectedItem"
    max-width="48rem"
    :aria-labelledby="detailTitleId"
    @update:model-value="!$event && (selectedId = undefined)"
  >
    <v-card
      v-if="selectedItem"
      class="metadata-items__panel d-flex flex-column"
    >
      <v-toolbar flat color="primary" density="comfortable" class="shrink-0">
        <v-card-title
          :id="detailTitleId"
          class="metadata-items__title hs-text-md"
        >
          {{ kindLabel }} details
        </v-card-title>
      </v-toolbar>
      <div class="metadata-items__content grow overflow-y-auto">
        <dl class="metadata-items__details hs-text-sm">
          <div>
            <dt class="hs-label">Scope</dt>
            <dd><MetadataScopeChip :scope="itemScope(selectedItem)" /></dd>
          </div>
          <div>
            <dt class="hs-label">UUID</dt>
            <dd class="metadata-items__uuid">
              <span class="hs-font-data">{{ selectedItem.id }}</span>
              <HsCopyButton
                :value="selectedItem.id"
                :label="itemTitle(selectedItem)"
                @copied="Snackbar.success('Metadata UUID copied to clipboard')"
                @error="Snackbar.error('Failed to copy metadata UUID')"
              />
            </dd>
          </div>
          <div v-for="field in fields" :key="field.key">
            <dt class="hs-label">{{ field.label }}</dt>
            <dd>
              <a
                v-if="field.link && safeLink(selectedItem[field.key])"
                :href="safeLink(selectedItem[field.key])"
                target="_blank"
                rel="noopener noreferrer"
                >{{ selectedItem[field.key] }}</a
              >
              <template v-else>{{
                selectedItem[field.key] || 'Not provided'
              }}</template>
            </dd>
          </div>
        </dl>
      </div>
      <v-card-actions class="metadata-items__panel-actions shrink-0">
        <v-spacer />
        <v-btn-cancel @click="selectedId = undefined">Close</v-btn-cancel>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts" generic="T extends MetadataItem">
import { computed, ref, useId } from 'vue'
import { mdiChevronRight } from '@mdi/js'
import { HsCopyButton, HsTableSummary } from '@hydroserver/design-system/vue'
import MetadataScopeChip from './MetadataScopeChip.vue'
import { Snackbar } from '@/utils/notifications'
import type { ItemScope } from '@/composables/tableScope'

import type { MetadataItem } from './metadataItem'

type MetadataKind =
  | 'method'
  | 'observedProperty'
  | 'processingLevel'
  | 'unit'
  | 'resultQualifier'
type FieldKey = Exclude<keyof MetadataItem, 'id' | '_scope'>
interface Field {
  key: FieldKey
  label: string
  link?: boolean
}

const props = defineProps<{
  items: T[]
  kind: MetadataKind
  loading: boolean
  search?: string
  defaultScope: ItemScope
  showScope?: boolean
}>()
defineSlots<{ actions(props: { item: T }): any }>()

const selectedId = ref<string>()
const detailTitleId = useId()
const selectedItem = computed(() =>
  props.items.find((item) => item.id === selectedId.value)
)
const titleKey = 'name'
const kindLabel = computed(
  () =>
    ({
      method: 'Method',
      observedProperty: 'Observed property',
      processingLevel: 'Processing level',
      unit: 'Unit',
      resultQualifier: 'Result qualifier',
    })[props.kind]
)
const fields = computed<Field[]>(() => {
  const result: Field[] = []
  result.push({ key: 'name', label: 'Name' })
  if (['method', 'observedProperty', 'unit'].includes(props.kind)) {
    result.push({ key: 'type', label: 'Type' })
  }
  if (props.kind === 'unit') {
    result.push({ key: 'symbol', label: 'Symbol' })
  } else {
    result.push({
      key: 'code',
      label: 'Code',
    })
    result.push({ key: 'description', label: 'Description' })
  }
  if (props.kind !== 'resultQualifier')
    result.push({ key: 'definition', label: 'Definition', link: true })
  if (props.kind === 'method') {
    result.push(
      { key: 'sensorModelManufacturer', label: 'Sensor model manufacturer' },
      { key: 'sensorModel', label: 'Sensor model' },
      {
        key: 'sensorModelDefinition',
        label: 'Sensor model definition',
        link: true,
      }
    )
  }
  return result
})
const headers = computed(() => [
  { title: kindLabel.value, key: titleKey },
  {
    title: 'Actions',
    key: 'actions',
    sortable: false,
    align: 'end' as const,
  },
])
const itemTitle = (item: T) => item[titleKey] || kindLabel.value
const itemScope = (item: T) => item._scope ?? props.defaultScope
const summaryFields: Record<MetadataKind, FieldKey[]> = {
  method: ['type', 'code'],
  observedProperty: ['type', 'code'],
  processingLevel: ['code', 'description'],
  unit: ['type', 'symbol'],
  resultQualifier: ['code', 'description'],
}
const summaryDetails = (item: T) =>
  summaryFields[props.kind].map((key) => {
    const value = item[key]
    if (value?.trim()) return value
    const label = fields.value.find((field) => field.key === key)!.label
    return `${label} not provided`
  })

// Search the metadata itself, including fields moved out of table columns.
const filteredItems = computed(() => {
  const query = props.search?.trim().toLocaleLowerCase()
  if (!query) return props.items
  return props.items.filter((item) =>
    [
      item.id,
      itemScope(item),
      ...fields.value.map((field) => item[field.key]),
    ].some((value) => value?.toLocaleLowerCase().includes(query))
  )
})

function safeLink(value: string | null | undefined) {
  if (!value) return undefined
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined
  } catch {
    return undefined
  }
}
</script>

<style scoped>
.metadata-items :deep(table) {
  table-layout: fixed;
}
.metadata-items :deep(th:last-child),
.metadata-items :deep(td:last-child) {
  width: calc(6 * var(--hs-space-32));
}
.metadata-items__actions,
.metadata-items__uuid {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
}
.metadata-items__actions {
  justify-content: flex-end;
  gap: var(--hs-space-2);
}
.metadata-items :deep(.hs-table-summary__details .metadata-items__scope) {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  overflow: visible;
}
.metadata-items__title {
  min-width: 0;
  overflow: hidden;
  color: rgb(var(--v-theme-on-primary));
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metadata-items__panel {
  max-height: 90vh;
  overflow: hidden;
  border-radius: var(--hs-radius-lg);
}
.metadata-items__content {
  min-height: 0;
  padding: var(--hs-space-16) var(--hs-space-24);
}
.metadata-items__panel-actions {
  background: var(--hs-surface);
  border-top: 1px solid var(--hs-border);
}
.metadata-items__details dt {
  color: var(--hs-text-secondary);
}
.metadata-items__details > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: var(--hs-space-16);
  padding-block: var(--hs-space-12);
  border-bottom: 1px solid var(--hs-border);
}
.metadata-items__details dd {
  margin: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.metadata-items__details a {
  color: rgb(var(--v-theme-primary));
}
.metadata-items__uuid {
  flex-wrap: wrap;
}
@media (max-width: 40rem) {
  .metadata-items :deep(th:last-child),
  .metadata-items :deep(td:last-child) {
    width: calc(3 * var(--hs-space-32));
  }
  .metadata-items__actions {
    flex-wrap: wrap;
  }
  .metadata-items__details > div {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--hs-space-8);
  }
}
</style>
