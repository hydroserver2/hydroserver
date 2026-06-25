<template>
  <v-card class="datastream-info-card" rounded="lg">
    <v-toolbar flat color="primary" density="comfortable">
      <v-icon icon="mdi-database-outline" class="ms-4 me-2" />
      <v-toolbar-title class="text-white font-weight-medium">
        Datastream Information
      </v-toolbar-title>
      <v-spacer />
      <v-btn
        :loading="downloading"
        prepend-icon="mdi-download"
        variant="tonal"
        color="white"
        class="me-2"
        @click="downloadDatastream(datastream.id)"
      >
        Download CSV
      </v-btn>
    </v-toolbar>

    <div v-if="datastream.name || datastream.description" class="pa-4 bg-grey-lighten-5">
      <div v-if="datastream.name" class="text-title-large text-grey-darken-3">
        {{ datastream.name }}
      </div>
      <div
        v-if="datastream.description"
        class="text-body-medium text-medium-emphasis mt-1"
      >
        {{ datastream.description }}
      </div>
      <div class="d-flex flex-wrap ga-2 mt-3">
        <v-chip
          v-if="datastream.thing"
          size="small"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-map-marker"
          :title="`Filter table by site: ${datastream.thing.name}`"
          @click="filterBySite"
        >
          {{ datastream.thing.samplingFeatureCode || datastream.thing.name || '–' }}
        </v-chip>
        <v-chip
          v-if="datastream.observedProperty"
          size="small"
          color="blue-grey"
          variant="tonal"
          prepend-icon="mdi-water"
          :title="`Filter table by observed property: ${datastream.observedProperty.name}`"
          @click="filterByObservedProperty"
        >
          {{ datastream.observedProperty.name || '–' }}
        </v-chip>
        <v-chip
          v-if="datastream.processingLevel"
          size="small"
          color="deep-purple"
          variant="tonal"
          prepend-icon="mdi-layers"
          :title="`Filter table by processing level: ${datastream.processingLevel.definition}`"
          @click="filterByProcessingLevel"
        >
          {{ datastream.processingLevel.code || '–' }}
        </v-chip>
        <v-chip
          size="small"
          color="teal"
          variant="tonal"
          prepend-icon="mdi-counter"
        >
          {{ datastream.valueCount?.toLocaleString() ?? 0 }} observations
        </v-chip>
        <v-chip
          size="small"
          :color="datastream.isPrivate ? 'orange' : 'green'"
          variant="tonal"
          :prepend-icon="datastream.isPrivate ? 'mdi-lock' : 'mdi-lock-open-variant'"
        >
          {{ datastream.isPrivate ? 'Private' : 'Public' }}
        </v-chip>
      </div>
    </div>

    <v-divider />

    <v-card-text class="pa-0 bg-grey-lighten-4">
      <v-expansion-panels
        v-model="expandedPanels"
        multiple
        variant="accordion"
        class="datastream-info-panels"
      >
        <v-expansion-panel value="general">
          <v-expansion-panel-title>
            <template #default>
              <v-icon icon="mdi-information-outline" color="primary" class="me-3" />
              <span class="font-weight-medium">General</span>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <MetadataList :items="generalItems">
              <template #value="{ item }">
                <template v-if="item.label === 'Tags'">
                  <span v-if="!(item.value as any[])?.length" class="text-medium-emphasis">
                    No tags
                  </span>
                  <div v-else class="d-flex flex-wrap ga-1 mt-1">
                    <v-chip
                      v-for="(tag, i) in (item.value as Tag[])"
                      :key="`${tag.key}-${i}`"
                      size="small"
                      color="blue-grey-lighten-4"
                      variant="flat"
                      class="tag-chip"
                    >
                      <strong>{{ tag.key }}</strong>:&nbsp;{{ tag.value }}
                    </v-chip>
                  </div>
                </template>
                <template v-else>
                  <span>{{ item.value ?? '–' }}</span>
                </template>
              </template>
            </MetadataList>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel value="location">
          <v-expansion-panel-title>
            <template #default>
              <v-icon icon="mdi-map-marker-outline" color="primary" class="me-3" />
              <span class="font-weight-medium">Site &amp; Location</span>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <MetadataList :items="locationItems" />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel value="sensor">
          <v-expansion-panel-title>
            <template #default>
              <v-icon icon="mdi-gauge" color="primary" class="me-3" />
              <span class="font-weight-medium">Sensor</span>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <MetadataList :items="sensorItems" />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel value="observedProperty">
          <v-expansion-panel-title>
            <template #default>
              <v-icon icon="mdi-water-outline" color="primary" class="me-3" />
              <span class="font-weight-medium">Observed Property</span>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <MetadataList :items="observedPropertyItems" />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel value="unit">
          <v-expansion-panel-title>
            <template #default>
              <v-icon icon="mdi-ruler" color="primary" class="me-3" />
              <span class="font-weight-medium">Unit</span>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <MetadataList :items="unitItems" />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel value="processingLevel">
          <v-expansion-panel-title>
            <template #default>
              <v-icon icon="mdi-layers-outline" color="primary" class="me-3" />
              <span class="font-weight-medium">Processing Level</span>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <MetadataList :items="processingLevelItems" />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <v-divider />

    <v-card-actions class="pa-3 bg-grey-lighten-5">
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary
        prepend-icon="mdi-plus"
        color="blue-lighten-3"
        @click="addToPlot(datastream)"
      >
        Add to Current Plot
      </v-btn-primary>
      <v-btn-primary
        type="submit"
        prepend-icon="mdi-chart-line"
        @click="clearAndPlot(datastream)"
      >
        Clear and Plot
      </v-btn-primary>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { computed, onMounted, ref, h } from 'vue'
import {
  Datastream,
  type DatastreamExtended,
  type Tag,
} from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { formatTimeWithZone } from '@/utils/time'
import { downloadDatastreamCsv } from '@/utils/csvExport'

const { hs } = storeToRefs(useHydroServer())

const props = defineProps({
  datastream: {
    type: Object as () => Datastream & DatastreamExtended,
    required: true,
  },
})
const emit = defineEmits(['close'])

const {
  selectedThings,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
  things,
} = storeToRefs(useDataVisStore())
const { plotDatastream, setPlottedDatastreams } = useDataVisStore()
const downloading = ref(false)
const tags = ref<Tag[]>([])
const expandedPanels = ref<string[]>(['general'])

function filterBySite() {
  const thing = props.datastream.thing
  if (!thing) return
  // Reuse the catalog reference so DatastreamFilters' v-checkbox equality works.
  const resolved = things.value.find((t) => t.id === thing.id) ?? thing
  selectedThings.value = [resolved]
  emit('close')
}

function filterByObservedProperty() {
  const name = props.datastream.observedProperty?.name
  if (!name) return
  selectedObservedPropertyNames.value = [name]
  emit('close')
}

function filterByProcessingLevel() {
  const def = props.datastream.processingLevel?.definition
  if (!def) return
  selectedProcessingLevelNames.value = [def]
  emit('close')
}

const MetadataList = (props: { items: { label: string; value: any }[] }, { slots }: any) =>
  h(
    'dl',
    { class: 'metadata-list' },
    props.items.flatMap((item, index) => [
      h('dt', { key: `k-${index}`, class: 'metadata-list__key' }, item.label),
      h(
        'dd',
        { key: `v-${index}`, class: 'metadata-list__value' },
        slots.value
          ? slots.value({ item })
          : [item.value === null || item.value === undefined || item.value === '' ? '–' : String(item.value)]
      ),
    ])
  )

const downloadDatastream = async (id: string) => {
  downloading.value = true
  try {
    await downloadDatastreamCsv(id)
  } catch (error) {
    console.error('Error downloading datastream', error)
  }
  downloading.value = false
}

const addToPlot = async (datastream: Datastream) => {
  emit('close')
  await plotDatastream(datastream)
}

const clearAndPlot = async (datastream: Datastream) => {
  emit('close')
  await setPlottedDatastreams([datastream], datastream.id)
}

const d = computed(() => props.datastream)

const generalItems = computed(() => [
  { label: 'Workspace Name', value: d.value.workspace?.name },
  { label: 'Datastream Name', value: d.value.name },
  { label: 'Description', value: d.value.description },
  { label: 'Number Of Observations', value: d.value.valueCount?.toLocaleString() },
  { label: 'Date Last Updated', value: formatTimeWithZone(d.value.phenomenonEndTime) },
  { label: 'Begin Date', value: formatTimeWithZone(d.value.phenomenonBeginTime) },
  { label: 'End Date', value: formatTimeWithZone(d.value.phenomenonEndTime) },
  { label: 'Data Type', value: d.value.observationType },
  { label: 'Value Type', value: d.value.resultType },
  { label: 'Sample Medium', value: d.value.sampledMedium },
  { label: 'No-data Value', value: d.value.noDataValue },
  { label: 'Id', value: d.value.id },
  { label: 'Aggregation Statistic', value: d.value.aggregationStatistic },
  { label: 'Intended Time Spacing', value: d.value.intendedTimeSpacing },
  { label: 'Intended Time Spacing Unit', value: d.value.intendedTimeSpacingUnit },
  { label: 'Time Aggregation Interval', value: d.value.timeAggregationInterval },
  { label: 'Time Aggregation Interval Unit', value: d.value.timeAggregationIntervalUnit },
  { label: 'Tags', value: tags.value },
  { label: 'Is Private', value: d.value.isPrivate ? 'Yes' : 'No' },
  { label: 'Is Visible', value: d.value.isVisible ? 'Yes' : 'No' },
])

const locationItems = computed(() => {
  const t = d.value.thing
  if (!t) return []
  const l = t.location || ({} as any)
  return [
    { label: 'Site Name', value: t.name },
    { label: 'Site Code', value: t.samplingFeatureCode },
    { label: 'Description', value: t.description },
    { label: 'Site Type', value: t.siteType },
    { label: 'Latitude', value: l.latitude },
    { label: 'Longitude', value: l.longitude },
    { label: 'Elevation (m)', value: l.elevation_m },
    { label: 'Elevation Datum', value: l.elevationDatum },
    { label: 'State/Province/Region', value: l.adminArea1 },
    { label: 'County/District', value: l.adminArea2 },
    { label: 'Country', value: l.country },
    { label: 'Sampling Feature Type', value: t.samplingFeatureType },
    { label: 'Is Private', value: t.isPrivate ? 'Yes' : 'No' },
    { label: 'Thing Id', value: t.id },
  ]
})

const sensorItems = computed(() => {
  const s = d.value.sensor
  if (!s) return []
  return [
    { label: 'Name', value: s.name },
    { label: 'Description', value: s.description },
    { label: 'Manufacturer', value: s.manufacturer },
    { label: 'Model', value: s.model },
    { label: 'Method Type', value: s.methodType },
    { label: 'Method Code', value: s.methodCode },
    { label: 'Method Link', value: s.methodLink },
    { label: 'Encoding Type', value: s.encodingType },
    { label: 'Model Link', value: s.modelLink },
  ]
})

const observedPropertyItems = computed(() => {
  const op = d.value.observedProperty
  if (!op) return []
  return [
    { label: 'Name', value: op.name },
    { label: 'Definition', value: op.definition },
    { label: 'Description', value: op.description },
    { label: 'Type', value: op.type },
    { label: 'Code', value: op.code },
  ]
})

const unitItems = computed(() => {
  const u = d.value.unit
  if (!u) return []
  return [
    { label: 'Name', value: u.name },
    { label: 'Symbol', value: u.symbol },
    { label: 'Definition', value: u.definition },
    { label: 'Type', value: u.type },
  ]
})

const processingLevelItems = computed(() => {
  const pl = d.value.processingLevel
  if (!pl) return []
  return [
    { label: 'Code', value: pl.code },
    { label: 'Definition', value: pl.definition },
    { label: 'Explanation', value: pl.explanation },
  ]
})

onMounted(async () => {
  // Tags are not returned by expand_related; fetch separately.
  const existing = (d.value as any).tags
  if (Array.isArray(existing)) {
    tags.value = existing
    return
  }
  try {
    const res = await hs.value.datastreams.getTags(d.value.id)
    tags.value = res.ok && Array.isArray(res.data) ? res.data : []
  } catch (error) {
    console.error('Error fetching datastream tags', error)
    tags.value = []
  }
})
</script>

<style scoped lang="scss">
.datastream-info-card {
  overflow: hidden;
}

.datastream-info-panels :deep(.v-expansion-panel) {
  background-color: transparent;
}

.datastream-info-panels :deep(.v-expansion-panel-title) {
  background-color: rgb(var(--v-theme-surface));
  min-height: 48px;
}

.datastream-info-panels :deep(.v-expansion-panel-title--active) {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.datastream-info-panels :deep(.v-expansion-panel-text__wrapper) {
  padding: 0.75rem 1.5rem 1rem;
  background-color: rgb(var(--v-theme-surface));
}

.tag-chip {
  max-width: 100%;
  height: auto;
  min-height: 1.6rem;
}

.tag-chip :deep(.v-chip__content) {
  white-space: normal;
  overflow-wrap: anywhere;
}
</style>

<style>
.metadata-list {
  display: grid;
  grid-template-columns: minmax(180px, 32%) 1fr;
  margin: 0;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.metadata-list__key {
  font-family: inherit;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.56) !important;
  padding: 0.55rem 0.9rem;
  background-color: #f5f7fa;
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  margin: 0;
}

.metadata-list__value {
  margin: 0;
  color: rgba(0, 0, 0, 0.9) !important;
  font-size: 0.925rem !important;
  font-weight: 500 !important;
  padding: 0.55rem 0.9rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  word-break: break-word;
  background-color: #ffffff;
  display: flex;
  align-items: center;
  min-height: 2.25rem;
}

.metadata-list__key:nth-last-of-type(1),
.metadata-list__value:nth-last-of-type(1) {
  border-bottom: none;
}
</style>
