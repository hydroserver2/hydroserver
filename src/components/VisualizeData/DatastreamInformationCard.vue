<template>
  <v-card>
    <v-card-title>
      <div class="d-flex justify-space-between w-100">
        Datastream Information
        <v-btn
          :loading="downloading"
          prepend-icon="mdi-download"
          color="blue-lighten-3"
          @click="downloadDatastream(datastream.id)"
          >Download</v-btn
        >
      </div>
    </v-card-title>
    <v-divider />

    <v-card-text>
      <v-expansion-panels multiple>
        <v-expansion-panel title="General">
          <v-expansion-panel-text>
            <v-list dense>
              <v-list-item v-for="(item, index) in generalItems" :key="index">
                <strong>{{ item.label }}</strong
                >: {{ item.value }}
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Location">
          <v-expansion-panel-text>
            <v-list dense>
              <v-list-item v-for="(item, index) in locationItems" :key="index">
                <strong>{{ item.label }}</strong
                >: {{ item.value }}
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Observed Property">
          <v-expansion-panel-text>
            <v-list dense>
              <v-list-item
                v-for="(item, index) in observedPropertyItems"
                :key="index"
              >
                <strong>{{ item.label }}</strong
                >: {{ item.value }}
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Unit">
          <v-expansion-panel-text>
            <v-list dense>
              <v-list-item v-for="(item, index) in unitItems" :key="index">
                <strong>{{ item.label }}</strong
                >: {{ item.value }}
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Processing Level">
          <v-expansion-panel-text>
            <v-list dense>
              <v-list-item
                v-for="(item, index) in processingLevelItems"
                :key="index"
              >
                <strong>{{ item.label }}</strong
                >: {{ item.value }}
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <v-divider />

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary color="blue-lighten-3" @click="addToPlot(datastream)"
        >Add to Current Plot</v-btn-primary
      >
      <v-btn-primary type="submit" @click="clearAndPlot(datastream)"
        >Clear and Plot</v-btn-primary
      >
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { computed, onMounted, ref } from 'vue'
import { Datastream, Unit } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
const { hs } = storeToRefs(useHydroServer())

const props = defineProps({
  datastream: { type: Object as () => Datastream, required: true },
})
const emit = defineEmits(['close'])

const { processingLevels, observedProperties, things, plottedDatastreams } =
  storeToRefs(useDataVisStore())
const downloading = ref(false)

const downloadDatastream = async (id: string) => {
  downloading.value = true
  try {
    await hs.value.datastreams.downloadCsv(id)
  } catch (error) {
    console.error('Error downloading datastream', error)
  }
  downloading.value = false
}
const addToPlot = (datastream: Datastream) => {
  const index = plottedDatastreams.value.findIndex(
    (ds) => ds.id === datastream.id
  )
  if (index === -1) plottedDatastreams.value.push(datastream)
  emit('close')
}

const clearAndPlot = (datastream: Datastream) => {
  emit('close')
  plottedDatastreams.value = []
  plottedDatastreams.value.push(datastream)
}

const unit = ref<Unit | null>(null)

const matchingThing = computed(() => {
  return things.value.find((t) => t.id === props.datastream.thingId)
})

// TODO
// const primaryOwnerOrganizationName = computed(() => {
//   const primaryOwner: Owner | undefined = matchingThing.value?.owners.find(
//     (owner) => owner.isPrimaryOwner
//   )
//   return primaryOwner?.organizationName || 'No primary owner found'
// })

const generalItems = computed(() => [
  { label: 'Number Of Observations', value: props.datastream.valueCount },
  { label: 'Date Last Updated', value: props.datastream.phenomenonEndTime },
  { label: 'Begin Date', value: props.datastream.phenomenonBeginTime },
  { label: 'End Date', value: props.datastream.phenomenonEndTime },
  { label: 'Data Type', value: props.datastream.observationType },
  { label: 'Value Type', value: props.datastream.resultType },
  { label: 'Sample Medium', value: props.datastream.sampledMedium },
  // { label: 'Source Organization', value: primaryOwnerOrganizationName.value },
  { label: 'Source Description', value: props.datastream.description },
])

const locationItems = computed(() => {
  if (!matchingThing.value) return []

  const {
    name,
    samplingFeatureCode,
    siteType,
    location: { latitude, longitude, state, county },
  } = matchingThing.value

  return [
    { label: 'Site Code', value: samplingFeatureCode },
    { label: 'Site Name', value: name },
    { label: 'Latitude', value: latitude },
    { label: 'Longitude', value: longitude },
    { label: 'State/Province/Region', value: state },
    { label: 'County/District', value: county },
    { label: 'Site Type', value: siteType },
  ]
})

const observedPropertyItems = computed(() => {
  if (!props.datastream.observedPropertyId) return []

  const op = observedProperties.value.find(
    (op) => op.id === props.datastream.observedPropertyId
  )
  return op
    ? [
        { label: 'Name', value: op.name },
        { label: 'Definition', value: op.definition },
        { label: 'Description', value: op.description },
        { label: 'Type', value: op.type },
        { label: 'Code', value: op.code },
      ]
    : []
})

const unitItems = computed(() => {
  return unit.value
    ? [
        { label: 'Name', value: unit.value.name },
        { label: 'Symbol', value: unit.value.symbol },
        { label: 'Definition', value: unit.value.definition },
        { label: 'Type', value: unit.value.type },
      ]
    : []
})

const processingLevelItems = computed(() => {
  const pl = processingLevels.value.find(
    (pl) => pl.id === props.datastream.processingLevelId
  )
  return pl
    ? [
        { label: 'Code', value: pl.code },
        { label: 'Definition', value: pl.definition },
        { label: 'Explanation', value: pl.explanation },
      ]
    : []
})

onMounted(async () => {
  unit.value = (await hs.value.units.get(props.datastream.unitId)).data
})
</script>
