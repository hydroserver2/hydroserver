<template>
  <div class="d-flex flex-column">
    <div class="d-flex align-center justify-space-between my-2 table-title">
      <h5 class="text-h5">Datastreams</h5>

      <v-select
        label="Show/Hide columns"
        v-model="selectedHeaders"
        :items="selectableHeaders"
        item-text="title"
        item-value="key"
        multiple
        item-color="green"
        density="compact"
        variant="solo"
        hide-details
        max-width="200"
      >
        <template #selection="{ item, index }">
          <!-- Leave blank so nothing appears in the v-select box -->
        </template>
      </v-select>
    </div>

    <v-card class="flex-grow-1 d-flex flex-column">
      <v-toolbar flat color="blue-grey-lighten-4">
        <v-text-field
          class="mx-2"
          clearable
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search"
          hide-details
          density="compact"
          rounded
        />

        <v-spacer />

        <v-btn :disabled="!plottedDatastreams.length" @click="clearSelected">
          Clear Selected
        </v-btn>

        <v-btn @click="showOnlySelected = !showOnlySelected">
          {{ showOnlySelected ? 'Show All' : 'Show Selected' }}
        </v-btn>

        <v-btn
          :loading="downloading"
          :disabled="!plottedDatastreams.length"
          prepend-icon="mdi-download"
          @click="downloadSelected(plottedDatastreams)"
          >Download Selected</v-btn
        >
      </v-toolbar>

      <v-data-table-virtual
        :headers="headers.filter((header) => header.visible)"
        :items="tableItems"
        :sort-by="sortBy"
        multi-sort
        :search="search"
        style="min-height: 30vh; height: 0"
        fixed-header
        class="elevation-2 flex-grow-1"
        color="secondary"
        density="compact"
        @click:row="onRowClick"
        hover
      >
        <template #item.status="{ item }">
          <v-progress-circular
            v-if="loadingStates.get(item.id)"
            color="primary"
            size="small"
            indeterminate
          ></v-progress-circular>
          <template v-else-if="!!observationsRaw[item.id]">
            <v-icon
              color="primary"
              :title="`${observationsRaw[item.id].datetimes.length} observation(s)`"
              >mdi-database-check</v-icon
            >
          </template>
        </template>
        <template v-slot:item.plot="{ item }">
          <v-checkbox
            :model-value="isChecked(item)"
            :disabled="plottedDatastreams.length >= 5 && !isChecked(item)"
            class="d-flex align-self-center"
            density="compact"
            @change="() => toggleDatastream(item)"
          />
        </template>
      </v-data-table-virtual>
    </v-card>

    <v-dialog v-model="openInfoCard" width="50rem" v-if="selectedDatastream">
      <DatastreamInformationCard
        :datastream="selectedDatastream"
        @close="openInfoCard = false"
      />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { computed, reactive, ref } from 'vue'
import DatastreamInformationCard from './DatastreamInformationCard.vue'
import { useObservationStore } from '@/store/observations'
import { Datastream } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
const { observationsRaw } = storeToRefs(useObservationStore())
const { loadingStates } = storeToRefs(useDataVisStore())
const { hs } = storeToRefs(useHydroServer())

const {
  things,
  filteredDatastreams,
  plottedDatastreams,
  observedProperties,
  processingLevels,
} = storeToRefs(useDataVisStore())
const { toggleDatastream } = useDataVisStore()

const showOnlySelected = ref(false)
const openInfoCard = ref(false)
const downloading = ref(false)
const selectedDatastream = ref<Datastream | null>(null)

const downloadSelected = async (plottedDatastreams: Datastream[]) => {
  downloading.value = true
  try {
    await hs.value.datastreams.downloadCsvBatchZip(plottedDatastreams)
  } catch (error) {
    console.error('Error downloading selected datastreams', error)
  }
  downloading.value = false
}

const onRowClick = (event: Event, item: any) => {
  // If the click came from a checkbox, do nothing.
  const targetElement = event.target as HTMLElement
  if (targetElement.id && targetElement.id.startsWith('checkbox-')) return

  const selectedDatastreamId = item.item.id
  const foundDatastream = filteredDatastreams.value.find(
    (d) => d.id === selectedDatastreamId
  )
  if (foundDatastream) {
    selectedDatastream.value = foundDatastream
    openInfoCard.value = true
  } else selectedDatastream.value = null
}

const displayDatastreams = computed(() => {
  if (showOnlySelected.value) {
    return filteredDatastreams.value.filter((ds) =>
      plottedDatastreams.value.some((sds) => sds.id === ds.id)
    )
  } else {
    return filteredDatastreams.value
  }
})

const tableItems = computed(() => {
  return displayDatastreams.value.map((ds) => {
    const thing = things.value.find((t) => t.id === ds.thingId)

    const observedProperty = observedProperties.value.find(
      (p) => p.id == ds.observedPropertyId
    )
    const processingLevel = processingLevels.value.find(
      (p) => p.id == ds.processingLevelId
    )

    return {
      ...ds,
      siteCodeName: thing?.samplingFeatureCode,
      observedPropertyName: observedProperty?.name,
      qualityControlLevelDefinition: processingLevel?.definition,
    }
  })
})

function clearSelected() {
  showOnlySelected.value = false
  plottedDatastreams.value = []
}

const isChecked = (item: Datastream) =>
  plottedDatastreams.value.some((sds) => sds.id === item.id)

const search = ref()
const headers = reactive([
  { title: '', key: 'status', visible: true, width: 1 },
  { title: 'Plot', key: 'plot', visible: true, width: 1 },
  // { title: 'Select', key: 'select', visible: true, width: 1 },
  {
    title: 'Site code',
    key: 'siteCodeName',
    visible: true,
  },
  {
    title: 'Observed property',
    key: 'observedPropertyName',
    visible: true,
  },
  {
    title: 'Processing level',
    key: 'qualityControlLevelDefinition',
    visible: true,
  },
  {
    title: 'Number observations',
    key: 'valueCount',
    visible: true,
  },
  {
    title: 'Date last updated',
    key: 'phenomenonEndTime',
    visible: true,
  },
])

const selectableHeaders = computed(() => {
  return headers.filter(
    (header) => !['plot', 'select', 'status'].includes(header.key)
  )
})

const sortBy = [
  { key: 'siteCodeName' },
  { key: 'observedPropertyName' },
  { key: 'qualityControlLevelDefinition' },
  // { key: 'valueCount', order: 'desc' },
]
const selectedHeaders = computed({
  get: () =>
    headers.filter((header) => header.visible).map((header) => header.key),
  set: (keys) => {
    headers.forEach((header) => {
      header.visible = keys.includes(header.key)
    })
  },
})
</script>

<style scoped lang="scss">
:deep(.v-table .v-data-table__tr:nth-child(even) td) {
  background: #f7f7f7;
}

.table-title :deep(.v-field__input[data-no-activator]) {
  display: none;
}
</style>
