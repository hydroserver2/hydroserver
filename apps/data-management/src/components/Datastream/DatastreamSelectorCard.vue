<template>
  <v-card>
    <v-toolbar color="primary-darken-2">
      <v-card-title>{{ cardTitle }}</v-card-title>
    </v-toolbar>

    <v-card-text>
      <v-row>
        <v-col cols="6">
          <v-autocomplete
            v-model="selectedThingId"
            :items="things"
            item-title="name"
            item-value="id"
            variant="outlined"
            label="Select a site"
          >
          </v-autocomplete>
        </v-col>
      </v-row>

      <v-toolbar color="surface">
        <v-card-title class="opacity-90 text-medium-emphasis"
          >Select a datastream</v-card-title
        >
        <v-switch
          v-if="enforceUniqueSelections"
          class="ml-2"
          color="primary"
          v-model="showLinkedDatastreams"
          label="Show already linked"
          hide-details
        />
        <v-spacer />
        <v-text-field
          class="mx-4"
          clearable
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          label="Search"
          hide-details
          density="compact"
          variant="underlined"
          maxWidth="300"
        />
      </v-toolbar>
      <v-divider />
      <div
        style="max-height: 1000px; overflow-y: auto"
        v-if="filteredDatastreams.length"
      >
        <v-data-table-virtual
          :headers="headers"
          :items="tableItems"
          :sort-by="[{ key: 'observedPropertyName' }]"
          :search="search"
          @click:row="onRowClick"
          color="blue-darken-2"
          :row-props="getRowProps"
          :style="{ 'max-height': `50vh` }"
          fixed-header
          hover
          multi-sort
        >
          <template #item.description="{ item }">
            <v-tooltip activator="parent" location="top">
              {{ item.description }}
            </v-tooltip>

            <span class="clamp-2" style="--clamp-width: 220px">
              {{ item.description }}
            </span>
          </template>
          <template #item.name="{ item }">
            <v-tooltip activator="parent" location="top">
              {{ item.name }}
            </v-tooltip>

            <span class="clamp-2" style="--clamp-width: 220px">
              {{ item.name }}
            </span>
          </template>
          <template #item.id="{ item }">
            <span class="one-line">
              {{ item.id }}
            </span>
          </template>
          <template #item.resultType="{ item }">
            <span class="one-line">
              {{ item.resultType }}
            </span>
          </template>
          <template #item.unit="{ item }">
            <span class="one-line">
              {{ item.unit }}
            </span>
          </template>
          <template #item.sensor="{ item }">
            <span class="one-line">
              {{ item.sensor }}
            </span>
          </template>
        </v-data-table-virtual>
      </div>
      <template v-else-if="!selectedThingId">
        <v-card-text>
          Select a site in order to view its datastreams.
        </v-card-text>
      </template>
      <template v-else>
        <v-card-text> No datastreams found for this site. </v-card-text>
      </template>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
    </v-card-actions>
  </v-card>

  <v-dialog width="40rem" v-model="openLinkConflictModal">
    <v-card>
      <v-toolbar color="yellow-darken-2">
        <v-card-title class="text-medium-emphasis">
          <v-icon :icon="mdiAlert" class="mr-2" /> Conflicting links
        </v-card-title>
      </v-toolbar>
      <v-card-text v-if="currentSourceId">
        This datastream is already linked to a data connection. To reassign it
        here, you’ll first need to unlink it from that source.
      </v-card-text>
      <v-card-text v-else>
        This datastream is already being linked to another data connection in
        the Task form. Check your pending task configurations to make sure each
        one is mapping the sources to the correct targets.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="openLinkConflictModal = false"
          >Cancel</v-btn-cancel
        >
        <v-btn-primary
          v-if="currentSourceId"
          color="yellow-darken-2"
          @click="goToDataConnection"
        >
          View existing data connection
        </v-btn-primary>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { watch, onMounted, ref, computed } from 'vue'
import { DatastreamExtended, Thing, Workspace } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import { useRoute, useRouter } from 'vue-router'
import { formatTime } from '@/utils/time'
import hs from '@hydroserver/client'
import { mdiAlert, mdiMagnify } from '@mdi/js'
import { useOrchestrationStore } from '@/store/orchestration'

const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const { linkedDatastreams } = storeToRefs(useOrchestrationStore())

const router = useRouter()
const route = useRoute()

const datastreamsForThing = ref<DatastreamExtended[]>([])
const things = ref<Thing[]>([])
const selectedThingId = ref('')
const search = ref()
const openLinkConflictModal = ref(false)
const currentSourceId = ref('')

const emit = defineEmits(['selectedDatastream', 'close'])
const props = defineProps({
  cardTitle: { type: String, required: true },
  workspace: { type: Workspace, required: false },
  enforceUniqueSelections: { type: Boolean, default: false },
  draftDatastreams: {
    type: Array as () => DatastreamExtended[],
    required: false,
  },
})
const showLinkedDatastreams = ref(!props.enforceUniqueSelections)

const headers = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name' },
  { title: 'Observed property', key: 'observedPropertyName' },
  { title: 'Processing level', key: 'processingLevelDefinition' },
  { title: 'Description', key: 'description', sortable: false },
  { title: 'Observation type', key: 'observationType' },

  { title: 'No-data value', key: 'noDataValue' },
  { title: 'Aggregation statistic', key: 'aggregationStatistic' },
  { title: 'Unit', key: 'unitName' },
  { title: 'Sensor', key: 'sensorName' },

  { title: 'Phenomenon begin', key: 'phenomenonBeginTime', class: 'one-line' },
  { title: 'Phenomenon end', key: 'phenomenonEndTime' },

  { title: 'Sampled medium', key: 'sampledMedium' },
  { title: 'Intended spacing', key: 'intendedTimeSpacing' },
  { title: 'Spacing unit', key: 'intendedTimeSpacingUnit' },
  { title: 'Aggregation interval', key: 'timeAggregationInterval' },
  { title: 'Interval unit', key: 'timeAggregationIntervalUnit' },

  { title: 'Is private', key: 'isPrivate' },
  { title: 'Is data visible', key: 'isVisible' },
  { title: 'Result type', key: 'resultType' },
  { title: 'Value count', key: 'valueCount' },
] as const

watch(
  selectedThingId,
  async (newId) => {
    if (!newId) {
      datastreamsForThing.value = []
      return
    }

    datastreamsForThing.value = (await hs.datastreams.listAllItems({
      thing_id: [newId],
      expand_related: true,
    })) as unknown as DatastreamExtended[]
  },
  { immediate: true }
)

const filteredDatastreams = computed(() =>
  props.enforceUniqueSelections && !showLinkedDatastreams.value
    ? datastreamsForThing.value.filter((ds) => !isLinked(ds))
    : datastreamsForThing.value
)

const tableItems = computed(() =>
  filteredDatastreams.value.map((ds) => ({
    ...ds,
    observedPropertyName: ds.observedProperty?.name,
    sensorName: ds.sensor.name,
    processingLevelDefinition: ds.processingLevel.definition,
    unit: ds.unit.name,
    phenomenonBeginTime: formatTime(ds.phenomenonBeginTime),
    phenomenonEndTime: formatTime(ds.phenomenonEndTime),
    isPrivate: ds.isPrivate ? 'Yes' : 'No',
    isVisible: ds.isVisible ? 'Yes' : 'No',
  }))
)

const selectAndClose = (ds: DatastreamExtended) => {
  emit('selectedDatastream', ds)
  emit('close')
}

// TODO: Use updated API to check against Task targetIdentifiers
const linkedDatastreamIds = computed(
  () => new Set(linkedDatastreams.value.map((d) => String(d.id)))
)

const isLinked = (item: DatastreamExtended) => {
  const id = String(item.id)
  const inDraft =
    props.draftDatastreams?.some((d) => String(d.id) === id) ?? false
  const inExistingTasks = linkedDatastreamIds.value.has(id)
  return inDraft || inExistingTasks
  // const linkedSourceId = item.dataSource?.id ?? ''
  // return inDraft || linkedSourceId
}

function onRowClick(_: MouseEvent, { item }: { item: DatastreamExtended }) {
  if (!props.enforceUniqueSelections) return selectAndClose(item)

  // const linkedSourceId = item.dataSource?.id ?? ''
  const linkedSourceId = ''

  if (isLinked(item)) {
    openLinkConflictModal.value = true
    currentSourceId.value = String(linkedSourceId || '')
    return
  }

  selectAndClose(item)
}

const getRowProps = ({ item }: { item: DatastreamExtended }) => {
  if (props.enforceUniqueSelections)
    return {
      class: isLinked(item) ? 'bg-red-lighten-2 text--disabled' : '',
    }
  else return ''
}

function goToDataConnection() {
  if (!currentSourceId.value) return

  openLinkConflictModal.value = false

  const samePage =
    route.name === 'DataConnection' && route.params.id === currentSourceId.value

  if (samePage) {
    router.go(0)
  } else {
    router.push({
      name: 'DataConnection',
      params: { id: currentSourceId.value },
    })
  }
}

onMounted(async () => {
  const workspaceId = props.workspace
    ? props.workspace.id
    : selectedWorkspace.value!.id
  things.value = await hs.things.listAllItems({ workspace_id: [workspaceId] })
  things.value.sort((a, b) => a.name.localeCompare(b.name))
})
</script>

<style lang="scss" scoped>
.clamp-2 {
  min-width: var(--clamp-width, 120px);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2; /* show two lines */
  line-clamp: 2;
  overflow: hidden;
}

.one-line {
  white-space: nowrap;
  min-width: max-content;
}
</style>
