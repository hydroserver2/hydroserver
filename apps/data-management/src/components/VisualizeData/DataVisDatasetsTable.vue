<template>
  <div class="flex h-full min-h-0 flex-col">
    <v-card
      class="flex min-h-0 flex-1 flex-col elevation-2 max-[600px]:min-h-[520px]"
    >
      <v-sheet class="px-3 py-2 max-[600px]:px-2" color="secondary">
        <v-defaults-provider :defaults="{ VBtn: { variant: 'text' } }">
          <div
            class="flex items-center gap-3 max-[960px]:flex-wrap max-[600px]:flex-col max-[600px]:items-stretch"
          >
            <h5
              class="m-0 px-1 whitespace-nowrap text-h5 max-[600px]:w-full max-[600px]:text-center"
            >
              Datastreams
            </h5>

            <v-text-field
              class="w-[135px] max-w-full flex-none max-[600px]:w-full"
              clearable
              v-model="search"
              :prepend-inner-icon="mdiMagnify"
              label="Search"
              hide-details
              density="compact"
              variant="underlined"
            />

            <div
              class="ml-auto flex flex-wrap items-center justify-end gap-2 max-[960px]:ml-0 max-[960px]:w-full max-[600px]:flex-col max-[600px]:items-stretch"
            >
              <v-btn
                class="max-[600px]:w-full"
                color="white"
                @click="clearSelected"
              >
                Clear Selected
              </v-btn>

              <v-btn
                class="max-[600px]:w-full"
                color="white"
                variant="outlined"
                @click="showOnlySelected = !showOnlySelected"
              >
                {{ showOnlySelected ? 'Show All' : 'Show Selected' }}
              </v-btn>

              <v-btn
                class="max-[600px]:w-full pr-0"
                color="white"
                :loading="downloading"
                :prepend-icon="mdiDownload"
                @click="downloadSelected(plottedDatastreams)"
                >Download Selected</v-btn
              >

              <v-menu :close-on-content-click="false" location="bottom end">
                <template #activator="{ props: menuProps }">
                  <template v-if="isMobile">
                    <v-btn
                      v-bind="menuProps"
                      color="white"
                      variant="text"
                      :prepend-icon="mdiTableColumnWidth"
                      class="max-[600px]:w-full"
                    >
                      Show/Hide Columns
                    </v-btn>
                  </template>
                  <template v-else>
                    <v-tooltip
                      text="Show/Hide Columns"
                      location="top"
                      :open-delay="0"
                      :close-delay="0"
                    >
                      <template #activator="{ props: tooltipProps }">
                        <v-btn
                          v-bind="{ ...menuProps, ...tooltipProps }"
                          :icon="mdiTableColumnWidth"
                          color="white"
                          variant="text"
                          class="shrink-0"
                          aria-label="Show or hide columns"
                        />
                      </template>
                    </v-tooltip>
                  </template>
                </template>

                <v-card class="min-w-[260px] py-1">
                  <v-list density="compact" class="py-1">
                    <v-list-item
                      v-for="header in selectableHeaders"
                      :key="header.key"
                      class="cursor-pointer"
                      @click="toggleHeader(header.key)"
                    >
                      <template #prepend>
                        <v-checkbox-btn
                          :model-value="selectedHeaders.includes(header.key)"
                          @update:model-value="toggleHeader(header.key)"
                          @click.stop
                          :aria-label="`Toggle ${header.title}`"
                          color="green"
                        />
                      </template>
                      <v-list-item-title>{{ header.title }}</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-card>
              </v-menu>
            </div>
          </div>
        </v-defaults-provider>
      </v-sheet>
      <v-data-table-virtual
        v-if="isMobile"
        :headers="headers.filter((header) => header.visible)"
        :items="tableItems"
        :search="search"
        fixed-header
        hide-default-header
        class="h-full min-h-0 flex-1 elevation-2 max-[600px]:min-h-[440px] [&_.v-table__wrapper]:overflow-x-hidden"
        color="green"
        density="compact"
        hover
      >
        <template v-slot:item="{ item }">
          <tr class="align-top">
            <td class="px-4 py-3" :colspan="headers.length">
              <div class="flex flex-col items-start gap-1.5">
                <div class="pt-1 text-base font-semibold leading-snug">
                  {{ item.name }}
                </div>
                <v-checkbox
                  :model-value="isChecked(item)"
                  :disabled="plottedDatastreams.length >= 5 && !isChecked(item)"
                  density="compact"
                  label="Plot"
                  hide-details
                  class="plot-checkbox"
                  @click.stop
                  @change="() => updatePlottedDatastreams(item)"
                />
              </div>
              <div class="flex flex-col gap-0.5 pt-1.5">
                <span class="text-xs uppercase tracking-[0.04em] text-black/55"
                  >Site</span
                >
                <span>{{ item.siteCodeName || '—' }}</span>
              </div>
              <div class="flex flex-col gap-0.5 pt-1.5">
                <span class="text-xs uppercase tracking-[0.04em] text-black/55"
                  >Observed property</span
                >
                <span>{{ item.observedPropertyName || '—' }}</span>
              </div>
              <div class="flex flex-col gap-0.5 pt-1.5">
                <span class="text-xs uppercase tracking-[0.04em] text-black/55"
                  >Processing level</span
                >
                <span>{{ item.qualityControlLevelDefinition || '—' }}</span>
              </div>
              <div class="flex flex-col gap-0.5 pt-1.5">
                <span class="text-xs uppercase tracking-[0.04em] text-black/55"
                  >Observations</span
                >
                <span>{{ item.valueCount ?? '—' }}</span>
              </div>
              <div class="flex flex-col gap-0.5 pt-1.5">
                <span class="text-xs uppercase tracking-[0.04em] text-black/55"
                  >Last updated</span
                >
                <span>{{ formatTime(item.phenomenonEndTime) }}</span>
              </div>
              <v-btn
                class="mt-3 mb-1 min-h-[36px] w-full"
                variant="outlined"
                color="primary"
                @click="openMetadata(item)"
              >
                Show Full Metadata
              </v-btn>
            </td>
          </tr>
        </template>
      </v-data-table-virtual>
      <v-data-table-virtual
        v-else
        :headers="headers.filter((header) => header.visible)"
        :items="tableItems"
        :sort-by="sortBy"
        multi-sort
        :search="search"
        fixed-header
        class="h-full min-h-0 flex-1 elevation-2 max-[600px]:min-h-[440px]"
        color="green"
        density="compact"
        @click:row="onRowClick"
        hover
      >
        <template v-slot:item.plot="{ item }">
            <v-checkbox
              :model-value="isChecked(item)"
              :disabled="plottedDatastreams.length >= 5 && !isChecked(item)"
              class="d-flex align-self-center plot-checkbox"
              density="compact"
              @click.stop
              @change="() => updatePlottedDatastreams(item)"
            />
        </template>
        <template v-slot:item.phenomenonEndTime="{ item }">
          {{ formatTime(item.phenomenonEndTime) }}
        </template>
      </v-data-table-virtual>
    </v-card>

    <v-dialog
      v-model="openInfoCard"
      width="50rem"
      v-if="selectedDatastream && selectedThing"
    >
      <DatastreamInformationCard
        :datastream="selectedDatastream"
        :thing="selectedThing"
        @close="openInfoCard = false"
      />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import hs, { Datastream, Thing } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { useDisplay } from 'vuetify'
import DatastreamInformationCard from './DatastreamInformationCard.vue'
import { formatTime } from '@/utils/time'
import { mdiDownload, mdiMagnify, mdiTableColumnWidth } from '@mdi/js'

const {
  things,
  filteredDatastreams,
  plottedDatastreams,
  observedProperties,
  processingLevels,
  tableHeaders: headers,
} = storeToRefs(useDataVisStore())

const showOnlySelected = ref(false)
const openInfoCard = ref(false)
const downloading = ref(false)
const selectedDatastream = ref<Datastream | null>(null)
const selectedThing = ref<Thing | null>(null)
const { smAndDown } = useDisplay()
const isMobile = computed(() => smAndDown.value)

const downloadSelected = async (plottedDatastreams: Datastream[]) => {
  downloading.value = true
  try {
    await hs.datastreams.downloadCsvBatchZip(plottedDatastreams)
  } catch (error) {
    console.error('Error downloading selected datastreams', error)
  }
  downloading.value = false
}

const onRowClick = (event: Event, item: any) => {
  // If the click came from a checkbox, do nothing.
  let targetElement = event.target as HTMLElement
  if (targetElement.id && targetElement.id.startsWith('checkbox-')) return

  const foundThing = things.value.find((t) => t.id === item.item.thingId)
  if (foundThing) selectedThing.value = foundThing

  const selectedDatastreamId = item.item.id
  const foundDatastream = filteredDatastreams.value.find(
    (d) => d.id === selectedDatastreamId
  )
  if (foundDatastream) {
    selectedDatastream.value = foundDatastream
    openInfoCard.value = true
  } else selectedDatastream.value = null
}

const openMetadata = (item: Datastream) => {
  const foundThing = things.value.find((t) => t.id === item.thingId)
  if (foundThing) selectedThing.value = foundThing

  const foundDatastream = filteredDatastreams.value.find(
    (d) => d.id === item.id
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
      (p) => p.id === ds.observedPropertyId
    )
    const observedPropertyCode =
      typeof observedProperty?.code === 'string'
        ? observedProperty.code.trim()
        : ''
    const observedPropertyName =
      typeof observedProperty?.name === 'string'
        ? observedProperty.name.trim()
        : ''
    const observedPropertyDisplay = observedPropertyCode
      ? `${observedPropertyName} (${observedPropertyCode})`
      : observedPropertyName
    const processingLevel = processingLevels.value.find(
      (p) => p.id === ds.processingLevelId
    )
    return {
      ...ds,
      siteCodeName: thing?.samplingFeatureCode,
      observedPropertyName: observedPropertyDisplay,
      qualityControlLevelDefinition: processingLevel?.definition,
    }
  })
})

function clearSelected() {
  showOnlySelected.value = false
  plottedDatastreams.value = []
}

const isChecked = (item: Datastream) => {
  return computed(() =>
    plottedDatastreams.value.some((sds) => sds.id === item.id)
  ).value
}

const search = ref()
const selectableHeaders = computed(() => {
  return headers.value.filter((header) => header.key !== 'plot')
})

const sortBy = [
  { key: 'siteCodeName' },
  { key: 'observedPropertyName' },
  { key: 'qualityControlLevelDefinition' },
]
const selectedHeaders = computed({
  get: () =>
    headers.value
      .filter((header) => header.visible)
      .map((header) => header.key),
  set: (keys) => {
    headers.value.forEach((header) => {
      header.visible = keys.includes(header.key)
    })
  },
})

const toggleHeader = (key: string) => {
  const keys = [...selectedHeaders.value]
  const index = keys.indexOf(key)
  if (index >= 0) {
    keys.splice(index, 1)
  } else {
    keys.push(key)
  }
  selectedHeaders.value = keys
}

function updatePlottedDatastreams(datastream: Datastream) {
  const index = plottedDatastreams.value.findIndex(
    (ds) => ds.id === datastream.id
  )
  if (index === -1) {
    if (plottedDatastreams.value.length >= 5) return
    plottedDatastreams.value.push(datastream)
  }
  else plottedDatastreams.value.splice(index, 1)
}
</script>

<style scoped>
:deep(.plot-checkbox.v-input--disabled .v-selection-control__input) {
  position: relative;
}

:deep(.plot-checkbox.v-input--disabled .v-selection-control__input::after) {
  content: '';
  position: absolute;
  inset: 4px;
  background:
    linear-gradient(
      45deg,
      transparent 46%,
      #94a3b8 46%,
      #94a3b8 54%,
      transparent 54%
    ),
    linear-gradient(
      -45deg,
      transparent 46%,
      #94a3b8 46%,
      #94a3b8 54%,
      transparent 54%
    );
  pointer-events: none;
}
</style>
