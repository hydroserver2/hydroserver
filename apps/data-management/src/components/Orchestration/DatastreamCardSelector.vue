<template>
  <v-autocomplete
    :model-value="modelValue"
    :items="selectorItems"
    item-title="title"
    item-value="value"
    :label="label"
    :placeholder="placeholder"
    :loading="loading"
    :disabled="disabled"
    :rules="rules"
    :density="density"
    :clearable="clearable"
    :hide-details="hideDetails"
    :menu-props="menuProps"
    no-data-text="No datastreams match your search."
    class="datastream-card-selector"
    @update:model-value="onUpdate"
  >
    <template #selection="{ item }">
      <span class="selected-datastream-name">
        {{ item.raw.datastream.name }}
      </span>
    </template>

    <template #item="{ props: itemProps, item }">
      <v-list-item
        v-bind="itemProps"
        :title="undefined"
        class="datastream-card-selector__item"
      >
        <DatastreamResultCard :datastream="item.raw.datastream" />
      </v-list-item>
    </template>
  </v-autocomplete>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Datastream } from '@hydroserver/client'
import DatastreamResultCard from './DatastreamResultCard.vue'

type Rule = (value: any) => true | string
type Density = 'default' | 'comfortable' | 'compact'

type DatastreamSelectorItem = {
  value: string
  title: string
  datastream: Datastream
}

const props = withDefaults(
  defineProps<{
    modelValue: string | null
    datastreams: Datastream[]
    label: string
    placeholder?: string
    loading?: boolean
    disabled?: boolean
    rules?: Rule[]
    density?: Density
    clearable?: boolean
    hideDetails?: boolean | 'auto'
  }>(),
  {
    placeholder: 'Search by name, site, property, unit...',
    loading: false,
    disabled: false,
    rules: () => [],
    density: 'default',
    clearable: true,
    hideDetails: false,
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void
}>()

const menuProps = {
  maxHeight: 480,
  contentClass: 'datastream-card-selector-menu',
}

const selectorItems = computed<DatastreamSelectorItem[]>(() =>
  props.datastreams.map((datastream) => ({
    value: datastream.id,
    title: searchText(datastream),
    datastream,
  }))
)

function onUpdate(value: unknown) {
  emit('update:modelValue', typeof value === 'string' ? value : null)
}

function searchText(datastream: Datastream): string {
  const ds = datastream as Datastream & Record<string, any>
  const related = [
    ds.thing?.name,
    ds.observedProperty?.name,
    ds.observedProperty?.code,
    ds.processingLevel?.code,
    ds.processingLevel?.definition,
    ds.unit?.name,
    ds.unit?.symbol,
    ds.sensor?.name,
    ds.sensor?.methodCode,
    ds.sensor?.methodType,
  ]

  return [
    datastream.id,
    datastream.name,
    datastream.sampledMedium,
    datastream.aggregationStatistic,
    datastream.valueCount,
    formatSpacing(datastream.intendedTimeSpacing, datastream.intendedTimeSpacingUnit),
    formatSpacing(datastream.timeAggregationInterval, datastream.timeAggregationIntervalUnit),
    ...related,
  ]
    .filter((value) => value !== null && value !== undefined && value !== '')
    .join(' ')
}

function formatSpacing(
  interval: number | null | undefined,
  unit: string | null | undefined
) {
  if (interval === null || interval === undefined || !unit) return ''
  return `${interval} ${unit}`
}
</script>

<style scoped>
.selected-datastream-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datastream-card-selector__item {
  padding: 0;
  border-radius: 8px;
  background: transparent;
}

.datastream-card-selector__item :deep(.v-list-item__content) {
  overflow: visible;
}

.datastream-card-selector__item :deep(.v-list-item__overlay),
.datastream-card-selector__item :deep(.v-list-item__underlay) {
  display: none;
}
</style>

<style>
.datastream-card-selector-menu .v-list {
  padding: 8px;
}

.datastream-card-selector-menu .v-list-item {
  margin: 0 0 8px;
  min-height: 0;
}

.datastream-card-selector-menu .v-list-item:last-child {
  margin-bottom: 0;
}

.datastream-card-selector-menu .v-list-item:hover .datastream-result-card,
.datastream-card-selector-menu .v-list-item--active .datastream-result-card {
  border-color: rgba(var(--v-theme-primary), 0.65);
}
</style>
