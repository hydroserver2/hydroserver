<template>
  <div class="datastream-result-card">
    <div class="datastream-result-card__title">{{ datastream.name }}</div>

    <div class="datastream-result-card__grid">
      <div
        v-for="detail in details"
        :key="detail.label"
        class="datastream-result-card__detail"
      >
        <div class="datastream-result-card__label">{{ detail.label }}</div>
        <div class="datastream-result-card__value">{{ detail.value }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Datastream } from '@hydroserver/client'

const props = defineProps<{
  datastream: Datastream
}>()

const details = computed(() => [
  { label: 'Site', value: relatedValue('thing', 'name') },
  { label: 'Processing level', value: processingLevel() },
  { label: 'Unit', value: unit() },
  { label: 'Intended time spacing', value: spacing(props.datastream.intendedTimeSpacing, props.datastream.intendedTimeSpacingUnit) },
  { label: 'Aggregation statistic & unit', value: aggregationStatisticAndUnit() },
  { label: 'Sensor (method)', value: sensorMethod() },
  { label: 'Sampled medium', value: props.datastream.sampledMedium || '-' },
  { label: 'Value count', value: formatCount(props.datastream.valueCount) },
])

function relatedValue(relation: string, key: string): string {
  const value = (props.datastream as Datastream & Record<string, any>)[relation]?.[key]
  return value ? String(value) : '-'
}

function processingLevel() {
  const pl = (props.datastream as Datastream & Record<string, any>).processingLevel
  if (!pl) return props.datastream.processingLevelId || '-'
  return [pl.code, pl.definition].filter(Boolean).join(' - ') || '-'
}

function unit() {
  const relatedUnit = (props.datastream as Datastream & Record<string, any>).unit
  return relatedUnit?.symbol || relatedUnit?.name || props.datastream.unitId || '-'
}

function aggregationStatisticAndUnit() {
  const statistic = humanize(props.datastream.aggregationStatistic)
  const interval = spacing(
    props.datastream.timeAggregationInterval,
    props.datastream.timeAggregationIntervalUnit
  )
  return [statistic, interval].filter(Boolean).join(', ') || '-'
}

function sensorMethod() {
  const sensor = (props.datastream as Datastream & Record<string, any>).sensor
  if (!sensor) return props.datastream.sensorId || '-'
  const method = sensor.methodCode || sensor.methodType
  if (sensor.name && method) return `${sensor.name} (${method})`
  return sensor.name || method || '-'
}

function spacing(
  interval: number | null | undefined,
  unit: string | null | undefined
) {
  if (interval === null || interval === undefined || !unit) return '-'
  return `${interval} ${unit}`
}

function formatCount(value: number | null | undefined) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat().format(value)
}

function humanize(value: string | null | undefined) {
  if (!value) return ''
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}
</script>

<style scoped>
.datastream-result-card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 14px 18px;
  width: 100%;
  background: rgb(var(--v-theme-surface));
}

.datastream-result-card__title {
  color: rgba(var(--v-theme-on-surface), 0.94);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 12px;
}

.datastream-result-card__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px 20px;
}

.datastream-result-card__label {
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.2;
}

.datastream-result-card__value {
  color: rgba(var(--v-theme-on-surface), 0.92);
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

@media (max-width: 760px) {
  .datastream-result-card__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
