<template>
  <h6 class="text-h6" style="color: #b71c1c">
    {{ thing!.dataDisclaimer }}
  </h6>

  <v-card>
    <div class="datastream-toolbar">
      <div class="datastream-toolbar__left">
        <h5 class="text-h6 datastream-toolbar__title">
          Datastreams available at this site
        </h5>
        <v-text-field
          v-model="search"
          clearable
          :prepend-inner-icon="mdiMagnify"
          label="Search"
          hide-details
          density="compact"
          variant="underlined"
          rounded="xl"
          class="datastream-search ml-2"
        />
      </div>
      <div class="datastream-toolbar__actions">
        <v-btn
          color="white"
          variant="outlined"
          :prependIcon="mdiChartLine"
          :to="{ name: 'VisualizeData', query: { sites: thing!.id } }"
          >View on Data Visualization Page</v-btn
        >
        <v-btn-add
          v-if="
            hasPermission(
              PermissionResource.Datastream,
              PermissionAction.Create,
              workspace
            )
          "
          color="white"
          :prependIcon="mdiPlus"
          @click="openCreate = true"
          >Add new datastream</v-btn-add
        >
      </div>
    </div>

    <div v-if="isMobile" class="datastream-mobile-list">
      <v-card
        v-for="item in mobileDatastreams"
        :key="item.id"
        class="datastream-card"
        variant="outlined"
      >
        <div class="datastream-card__content">
          <div class="datastream-card__title">
            {{ item.name || item.OPName }}
          </div>
          <div
            v-if="
              !hasPermission(
                PermissionResource.Datastream,
                PermissionAction.View,
                workspace
              ) && !item.isVisible
            "
            class="text-body-2"
          >
            Data is private for this datastream
          </div>
          <div v-else>
            <Sparkline
              class="mt-1"
              :datastream="item"
              @openChart="openCharts[item.id] = true"
              @latest-value="(value) => handleLatestValueUpdate(item.id, value)"
              :unitName="item.unitName"
            />
            <div
              v-if="Number(item.valueCount) > 0"
              class="mt-1 text-base leading-[1.3]"
              :class="latestStatusClass(item)"
            >
              <strong class="mr-2 font-semibold">Latest observation:</strong>
              <span class="font-semibold">{{ item.endDate }}</span>
            </div>
            <div
              v-if="shouldShowLatestValue(item.id)"
              class="mt-1 text-base leading-[1.3]"
              :class="latestStatusClass(item)"
            >
              <strong class="mr-2 font-semibold">Latest value:</strong>
              <span class="font-semibold">{{ latestValueDisplay(item) }}</span>
            </div>
          </div>

          <v-dialog v-model="openCharts[item.id]" width="80rem">
            <DatastreamPopupPlot
              :datastream="item"
              @close="openCharts[item.id] = false"
            />
          </v-dialog>

          <div class="datastream-info-list">
            <p class="datastream-line">
              <strong class="mr-2">Identifier:</strong>
              <span class="datastream-id">
                {{ item.id }}
                <v-tooltip text="Copy ID">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon
                      size="default"
                      variant="text"
                      class="datastream-copy-btn"
                      @click.stop="copyDatastreamId(item.id)"
                    >
                      <v-icon :icon="mdiContentCopy" size="small" />
                    </v-btn>
                  </template>
                </v-tooltip>
              </span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Sampled medium:</strong>
              <span>{{ item.sampledMedium }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Sensor:</strong>
              <span>{{ item.sensorName }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">No data value:</strong>
              <span>{{ item.noDataValue }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Begin date:</strong>
              <span>{{ item.beginDate }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">End date:</strong>
              <span>{{ item.endDate }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Number of observations:</strong>
              <span>{{ item.valueCount }}</span>
            </p>
          </div>
        </div>
        <div class="datastream-card__actions">
          <div class="datastream-card__icons">
            <v-tooltip
              bottom
              :openDelay="500"
              content-class="pa-0 ma-0 bg-transparent"
              v-if="
                hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.Edit,
                  workspace
                )
              "
            >
              <template #activator="{ props: tp }">
                <v-icon
                  v-bind="tp"
                  :icon="item.isVisible ? mdiFileEyeOutline : mdiFileRemove"
                  :color="item.isVisible ? 'green' : 'red-darken-2'"
                  small
                  @click="toggleDataVisibility(item)"
                />
              </template>

              <VisibilityTooltipCard
                title="Observations are currently"
                :items="[
                  {
                    label: 'Clicking this will',
                    value: item.isVisible
                      ? 'Hide data for this datastream from guests of your site while keeping the datastream metadata publicly visible.'
                      : 'Make the observations and metadata for this datastream visible to guests of your site.',
                  },
                ]"
                :is-visible="item.isVisible"
              />
            </v-tooltip>

            <v-tooltip
              bottom
              :openDelay="500"
              v-if="
                hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.Edit,
                  workspace
                )
              "
              content-class="pa-0 ma-0 bg-transparent"
            >
              <template v-slot:activator="{ props }">
                <v-icon
                  :icon="item.isPrivate ? mdiLock : mdiLockOpenVariant"
                  :color="item.isPrivate ? 'red-darken-2' : 'green'"
                  small
                  v-bind="props"
                  @click="toggleVisibility(item)"
                />
              </template>

              <VisibilityTooltipCard
                title="Datastream is currently"
                :items="[
                  {
                    label: 'Clicking this will',
                    value: item.isPrivate
                      ? 'Make this datastream and all its metadata and observations publicly visible.'
                      : 'Hide this datastream from guests of your site along with all its metadata and observations.',
                  },
                ]"
                :is-visible="!item.isPrivate"
              />
            </v-tooltip>

            <v-tooltip
              v-if="
                !hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.View,
                  workspace
                ) && !item.isVisible
              "
              bottom
              :openDelay="100"
            >
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" :icon="mdiLock" color="red-darken-2" />
              </template>
              <span>The data for this datastream is private </span>
            </v-tooltip>

            <v-menu v-else>
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" :icon="mdiDotsVertical" />
              </template>
              <v-list>
                <v-list-item
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Edit,
                      workspace
                    )
                  "
                  :prepend-icon="mdiPencil"
                  title="Edit datastream metadata"
                  @click="openDialog(item, 'edit')"
                />
                <div
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Delete,
                      workspace
                    )
                  "
                >
                  <v-list-item
                    :prepend-icon="mdiDelete"
                    title="Delete datastream"
                    @click="openDialog(item, 'delete')"
                  />
                </div>
                <v-list-item
                  v-if="
                    hasPermission(
                      PermissionResource.Observation,
                      PermissionAction.Delete,
                      workspace
                    )
                  "
                  :prepend-icon="mdiDeleteOutline"
                  title="Delete data from datastream"
                  @click="openObservationDialog(item)"
                />
                <v-list-item
                  :prepend-icon="mdiChartLine"
                  title="Visualize data"
                  :to="{
                    name: 'VisualizeData',
                    query: { sites: item.thingId, datastreams: item.id },
                  }"
                />
                <v-list-item
                  :prepend-icon="mdiDownload"
                  title="Download data"
                  @click="onDownload(item.id)"
                />
              </v-list>
            </v-menu>
          </div>
          <v-btn
            variant="outlined"
            class="datastream-card__meta-btn"
            @click="openInfoCardFor(item)"
          >
            View Full Metadata
          </v-btn>
          <div v-if="downloading[item.id]" class="datastream-download mt-2">
            <v-progress-circular
              indeterminate
              size="16"
              width="2"
              color="primary"
            />
            preparing file...
          </div>
        </div>
      </v-card>
    </div>

    <v-data-table-virtual
      v-else
      class="datastream-table"
      :headers="headers"
      :items="visibleDatastreams"
      :search="search"
      :sort-by="sortBy"
      :style="{ 'max-height': `100vh` }"
      fixed-header
    >
      <template v-slot:item.latest="{ item }">
        <div class="datastream-latest">
          <div class="datastream-title">
            {{ item.name || item.OPName }}
          </div>
          <div class="mt-2">
            <div
              v-if="
                !hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.View,
                  workspace
                ) && !item.isVisible
              "
              class="text-body-2"
            >
              Data is private for this datastream
            </div>
            <div v-else>
              <Sparkline
                class="mt-1"
                :datastream="item"
                @openChart="openCharts[item.id] = true"
                @latest-value="(value) => handleLatestValueUpdate(item.id, value)"
                :unitName="item.unitName"
              />
              <div
                v-if="Number(item.valueCount) > 0"
                class="mt-1 text-base leading-[1.3]"
                :class="latestStatusClass(item)"
              >
                <strong class="mr-2 font-semibold">Latest observation:</strong>
                <span class="font-semibold">{{ item.endDate }}</span>
              </div>
              <div
                v-if="shouldShowLatestValue(item.id)"
                class="mt-1 text-base leading-[1.3]"
                :class="latestStatusClass(item)"
              >
                <strong class="mr-2 font-semibold">Latest value:</strong>
                <span class="font-semibold">{{ latestValueDisplay(item) }}</span>
              </div>
            </div>
          </div>

          <v-dialog v-model="openCharts[item.id]" width="80rem">
            <DatastreamPopupPlot
              :datastream="item"
              @close="openCharts[item.id] = false"
            />
          </v-dialog>
        </div>
      </template>

      <template v-slot:item.info="{ item }">
        <div class="datastream-info-list">
          <p class="datastream-line">
            <strong class="mr-2">Identifier:</strong>
            <span class="datastream-id">
              {{ item.id }}
              <v-tooltip text="Copy ID">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    size="small"
                    variant="text"
                    @click.stop="copyDatastreamId(item.id)"
                  >
                    <v-icon :icon="mdiContentCopy" size="small" />
                  </v-btn>
                </template>
              </v-tooltip>
            </span>
          </p>
          <p class="datastream-line">
            <strong class="mr-2">Sampled medium:</strong>
            <span>{{ item.sampledMedium }}</span>
          </p>
          <p class="datastream-line">
            <strong class="mr-2">Sensor:</strong>
            <span>{{ item.sensorName }}</span>
          </p>
          <p class="datastream-line">
            <strong class="mr-2">No data value:</strong>
            <span>{{ item.noDataValue }}</span>
          </p>
          <p class="datastream-line">
            <strong class="mr-2">Begin date:</strong>
            <span>{{ item.beginDate }}</span>
          </p>
          <p class="datastream-line">
            <strong class="mr-2">End date:</strong>
            <span>{{ item.endDate }}</span>
          </p>
          <p class="datastream-line">
            <strong class="mr-2">Number of observations:</strong>
            <span>{{ item.valueCount }}</span>
          </p>
        </div>
      </template>

      <template v-slot:item.actions="{ item }">
        <div class="datastream-actions">
          <div class="datastream-actions__icons">
            <v-tooltip
              bottom
              :openDelay="500"
              content-class="pa-0 ma-0 bg-transparent"
              v-if="
                hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.Edit,
                  workspace
                )
              "
            >
              <template #activator="{ props: tp }">
                <v-icon
                  v-bind="tp"
                  :icon="item.isVisible ? mdiFileEyeOutline : mdiFileRemove"
                  :color="item.isVisible ? 'green' : 'red-darken-2'"
                  small
                  @click="toggleDataVisibility(item)"
                />
              </template>

              <VisibilityTooltipCard
                title="Observations are currently"
                :items="[
                  {
                    label: 'Clicking this will',
                    value: item.isVisible
                      ? 'Hide data for this datastream from guests of your site while keeping the datastream metadata publicly visible.'
                      : 'Make the observations and metadata for this datastream visible to guests of your site.',
                  },
                ]"
                :is-visible="item.isVisible"
              />
            </v-tooltip>

            <v-tooltip
              bottom
              :openDelay="500"
              v-if="
                hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.Edit,
                  workspace
                )
              "
              content-class="pa-0 ma-0 bg-transparent"
            >
              <template v-slot:activator="{ props }">
                <v-icon
                  :icon="item.isPrivate ? mdiLock : mdiLockOpenVariant"
                  :color="item.isPrivate ? 'red-darken-2' : 'green'"
                  small
                  v-bind="props"
                  @click="toggleVisibility(item)"
                />
              </template>

              <VisibilityTooltipCard
                title="Datastream is currently"
                :items="[
                  {
                    label: 'Clicking this will',
                    value: item.isPrivate
                      ? 'Make this datastream and all its metadata and observations publicly visible.'
                      : 'Hide this datastream from guests of your site along with all its metadata and observations.',
                  },
                ]"
                :is-visible="!item.isPrivate"
              />
            </v-tooltip>

            <v-tooltip
              v-if="
                !hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.View,
                  workspace
                ) && !item.isVisible
              "
              bottom
              :openDelay="100"
            >
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" :icon="mdiLock" color="red-darken-2" />
              </template>
              <span>The data for this datastream is private </span>
            </v-tooltip>

            <v-menu v-else>
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" :icon="mdiDotsVertical" />
              </template>
              <v-list>
                <v-list-item
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Edit,
                      workspace
                    )
                  "
                  :prepend-icon="mdiPencil"
                  title="Edit datastream metadata"
                  @click="openDialog(item, 'edit')"
                />
                <div
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Delete,
                      workspace
                    )
                  "
                >
                  <v-list-item
                    :prepend-icon="mdiDelete"
                    title="Delete datastream"
                    @click="openDialog(item, 'delete')"
                  />
                </div>
                <v-list-item
                  v-if="
                    hasPermission(
                      PermissionResource.Observation,
                      PermissionAction.Delete,
                      workspace
                    )
                  "
                  :prepend-icon="mdiDeleteOutline"
                  title="Delete data from datastream"
                  @click="openObservationDialog(item)"
                />
                <v-list-item
                  :prepend-icon="mdiChartLine"
                  title="Visualize data"
                  :to="{
                    name: 'VisualizeData',
                    query: { sites: item.thingId, datastreams: item.id },
                  }"
                />
                <v-list-item
                  :prepend-icon="mdiDownload"
                  title="Download data"
                  @click="onDownload(item.id)"
                />
              </v-list>
            </v-menu>
          </div>
          <v-btn
            variant="outlined"
            class="mt-2 datastream-meta-btn"
            @click="openInfoCardFor(item)"
          >
            View Full Metadata
          </v-btn>
          <div v-if="downloading[item.id]" class="datastream-download mt-2">
            <v-progress-circular
              indeterminate
              size="16"
              width="2"
              color="primary"
            />
            preparing file...
          </div>
        </div>
      </template>
    </v-data-table-virtual>
  </v-card>

  <v-dialog v-model="openCreate" width="80rem">
    <DatastreamForm
      :thing="thing!"
      :workspace="workspace"
      @close="openCreate = false"
      @created="onCreated"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="80rem">
    <DatastreamForm
      :thing="thing!"
      :workspace="workspace"
      :datastream="item"
      @close="openEdit = false"
      @updated="updateDatastream"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DatastreamDeleteCard
      :datastream="item"
      @close="openDelete = false"
      @delete="onDelete"
    />
  </v-dialog>

  <v-dialog v-model="openObservationsDelete" width="40rem">
    <ObservationsDeleteCard
      :datastream="item"
      @close="openObservationsDelete = false"
      @delete="onObservationsDelete"
    />
  </v-dialog>

  <v-dialog
    v-model="openInfoCard"
    width="50rem"
    v-if="selectedDatastream && thing"
  >
    <DatastreamTableInfoCard
      :datastream="selectedDatastream"
      :thing="thing"
      @close="openInfoCard = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import DatastreamPopupPlot from '@/components/Datastream/DatastreamPopupPlot.vue'
import DatastreamForm from '@/components/Datastream/DatastreamForm.vue'
import DatastreamDeleteCard from './DatastreamDeleteCard.vue'
import Sparkline from '@/components/Sparkline.vue'
import { computed, reactive, ref, toRef } from 'vue'
import { useMetadata } from '@/composables/useMetadata'
import { storeToRefs } from 'pinia'
import { useThingStore } from '@/store/thing'
import { Datastream, Workspace } from '@hydroserver/client'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useTableLogic } from '@/composables/useTableLogic'
import { Snackbar } from '@/utils/notifications'
import { formatTime } from '@/utils/time'
import DatastreamTableInfoCard from './DatastreamTableInfoCard.vue'
import ObservationsDeleteCard from '../Observation/ObservationsDeleteCard.vue'
import VisibilityTooltipCard from '@/components/Datastream/VisibilityTooltipCard.vue'
import hs, { PermissionAction, PermissionResource } from '@hydroserver/client'
import { useDisplay } from 'vuetify/lib/framework.mjs'
import {
  mdiChartLine,
  mdiContentCopy,
  mdiDelete,
  mdiDeleteOutline,
  mdiDotsVertical,
  mdiDownload,
  mdiFileEyeOutline,
  mdiFileRemove,
  mdiLock,
  mdiLockOpenVariant,
  mdiMagnify,
  mdiPencil,
  mdiPlus,
} from '@mdi/js'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})

const { thing } = storeToRefs(useThingStore())
const openCreate = ref(false)
const workspaceRef = toRef(props, 'workspace')
const thingIdRef = computed(() => thing.value!.id)
const downloading = reactive<Record<string, boolean>>({})
const search = ref()
const { smAndDown } = useDisplay()
const isMobile = computed(() => smAndDown.value)

const openObservationsDelete = ref(false)
function openObservationDialog(selectedItem: any) {
  item.value = selectedItem
  openObservationsDelete.value = true
}

const openInfoCard = ref(false)
const selectedDatastream = ref<Datastream | null>(null)
const openInfoCardFor = (datastream: Datastream) => {
  selectedDatastream.value = datastream
  openInfoCard.value = true
}

const { hasPermission } = useWorkspacePermissions(workspaceRef)

const updateDatastream = async (updatedDatastream: Datastream) => {
  await fetchMetadata(props.workspace.id)
  onUpdate(updatedDatastream)
}

const onCreated = async () => {
  await fetchMetadata(props.workspace.id)
  await loadDatastreams()
}

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  useTableLogic(
    async (thingId: string) =>
      await hs.datastreams.listAllItems({ thing_id: [thingId] }),
    hs.datastreams.delete,
    Datastream,
    thingIdRef
  )

const { sensors, units, observedProperties, processingLevels, fetchMetadata } =
  useMetadata(toRef(props, 'workspace'))

const openCharts = reactive<Record<string, boolean>>({})
const latestValues = reactive<
  Record<string, { text: string; showUnit: boolean; isBad: boolean }>
>({})

const handleLatestValueUpdate = (
  datastreamId: string,
  value: { text: string; showUnit: boolean; isBad: boolean }
) => {
  latestValues[datastreamId] = value
}

const latestValueFor = (datastreamId: string) =>
  latestValues[datastreamId] || { text: '—', showUnit: false, isBad: false }

const shouldShowLatestValue = (datastreamId: string) => {
  const value = latestValueFor(datastreamId)
  return value.text !== 'No observations'
}

const latestValueDisplay = (datastream: { id: string; unitName?: string }) => {
  const value = latestValueFor(datastream.id)
  if (!value.showUnit) return value.text
  return `${value.text} ${datastream.unitName ?? ''}`.trim()
}

const latestStatusClass = (datastream: Datastream) => {
  if (isDatastreamStale(datastream)) return 'text-[#9e9e9e]'
  const latestValue = latestValueFor(datastream.id)
  if (latestValue.isBad) return 'text-[#c86060]'
  return 'text-[#2e7d32]'
}

const visibleDatastreams = computed(() => {
  return items.value
    .filter(
      (d) =>
        !d.isPrivate ||
        hasPermission(
          PermissionResource.Datastream,
          PermissionAction.View,
          props.workspace
        )
    )
    .map((d) => {
      const unit = units.value.find((u) => u.id === d.unitId)
      const sensor = sensors.value.find((s) => s.id === d.sensorId)
      const op = observedProperties.value.find(
        (o) => o.id === d.observedPropertyId
      )
      const pl = processingLevels.value.find(
        (p) => p.id === d.processingLevelId
      )

      const mapped = {
        ...d,
        OPName: op ? `${op.name} (${op.code})` : '',
        processingLevelCode: pl?.code ?? '',
        processingLevelName: pl?.definition ?? '',
        sensorName: sensor?.name ?? '',
        unitName: unit?.name ?? '',
        searchText: ',',
        beginDate: formatTime(d.phenomenonBeginTime),
        endDate: formatTime(d.phenomenonEndTime),
        aggregationInterval: `${d.timeAggregationInterval} ${d.timeAggregationIntervalUnit}`,
        spacingInterval: `${d.intendedTimeSpacing} ${d.intendedTimeSpacingUnit}`,
      }

      mapped.searchText = [
        mapped.name,
        mapped.OPName,
        mapped.id,
        mapped.processingLevelName,
        mapped.sampledMedium,
        mapped.sensorName,
        mapped.noDataValue,
        mapped.aggregationStatistic,
        mapped.unitName,
        mapped.status,
        mapped.valueCount,
        mapped.beginDate,
        mapped.endDate,
        mapped.aggregationInterval,
        mapped.spacingInterval,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return mapped
    })
})

const normalizedSearch = computed(() =>
  (search.value ?? '').toString().trim().toLowerCase()
)

const isDatastreamStale = (datastream: Datastream) => {
  if (!datastream.phenomenonEndTime) return true
  const endTime = new Date(datastream.phenomenonEndTime)
  const seventyTwoHoursAgo = new Date(Date.now() - 72 * 60 * 60 * 1000)
  return endTime < seventyTwoHoursAgo
}

const mobileDatastreams = computed(() => {
  const sorted = [...visibleDatastreams.value].sort((a, b) =>
    (a.name || a.OPName || '').localeCompare(b.name || b.OPName || '')
  )

  if (!normalizedSearch.value) return sorted
  return sorted.filter((item) =>
    (item.searchText || '').includes(normalizedSearch.value)
  )
})

const onDownload = async (datastreamId: string) => {
  if (downloading[datastreamId]) return
  downloading[datastreamId] = true

  try {
    await hs.datastreams.downloadCsv(datastreamId)
  } catch (err: any) {
    console.error('Error downloading datastream CSV', err)
    Snackbar.error(err.message)
  } finally {
    downloading[datastreamId] = false
  }
}

async function toggleDataVisibility(computedDatastream: Datastream) {
  // mutate the original
  const datastream = items.value.find((d) => d.id === computedDatastream.id)
  if (!datastream) return

  datastream.isVisible = !datastream.isVisible
  if (datastream.isVisible) datastream.isPrivate = false
  patchDatastream({
    id: datastream.id,
    isPrivate: datastream.isPrivate,
    isVisible: datastream.isVisible,
  })
}

async function toggleVisibility(computedDatastream: Datastream) {
  // mutate the original
  const datastream = items.value.find((d) => d.id === computedDatastream.id)
  if (!datastream) return

  datastream.isPrivate = !datastream.isPrivate
  if (datastream.isPrivate) datastream.isVisible = false
  patchDatastream({
    id: datastream.id,
    isPrivate: datastream.isPrivate,
    isVisible: datastream.isVisible,
  })
}

const copyDatastreamId = async (id: string) => {
  try {
    await navigator.clipboard.writeText(id)
    Snackbar.success('Datastream ID copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy datastream ID')
  }
}

const patchDatastream = async <T extends { id: string }>(patchBody: T) => {
  try {
    await hs.datastreams.update(patchBody)
  } catch (error) {
    console.error('Error updating datastream', error)
  }
}

async function onObservationsDelete() {
  try {
    await hs.datastreams.deleteObservations(item.value.id)
    items.value = []
    await loadDatastreams()
  } catch (error) {
    console.error('Failed to delete observations', error)
    Snackbar.error('Failed to delete observations')
  }
  openObservationsDelete.value = false
}

const sortBy = [{ key: 'name' }]
const headers = [
  {
    title: 'Observation information',
    key: 'latest',
    sortable: false,
  },
  {
    title: 'Datastream information',
    key: 'info',
    value: 'searchText',
    sortable: false,
  },
  { title: 'Actions', key: 'actions', sortable: false },
]

const loadDatastreams = async () => {
  try {
    items.value = await hs.datastreams.listAllItems({
      thing_id: [thing.value!.id],
    })
  } catch (e) {
    console.error('Error fetching datastreams', e)
  }
}
</script>

<style scoped>
.datastream-table :deep(.v-data-table__td) {
  vertical-align: top;
  white-space: normal;
  padding-top: 0.4rem !important;
  padding-bottom: 0.4rem !important;
}

.datastream-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  padding: 0.75rem 1rem;
  background: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-on-secondary));
  border-radius: 12px 12px 0 0;
}

.datastream-toolbar__left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex: 1 1 420px;
  min-width: 220px;
}

.datastream-toolbar__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-left: auto;
}

.datastream-toolbar__title {
  margin: 0;
  line-height: 1.2;
  color: inherit;
}

.datastream-toolbar :deep(.v-field__input) {
  color: rgb(var(--v-theme-on-secondary));
}

.datastream-toolbar :deep(.v-field__prepend-inner) {
  color: rgba(var(--v-theme-on-secondary), 0.8);
}

.datastream-toolbar :deep(.v-label) {
  color: rgba(var(--v-theme-on-secondary), 0.8);
}

.datastream-toolbar :deep(.v-field__outline__start),
.datastream-toolbar :deep(.v-field__outline__end) {
  border-color: rgba(var(--v-theme-on-secondary), 0.5);
}

.datastream-toolbar :deep(.v-field__outline__notch) {
  border-color: rgba(var(--v-theme-on-secondary), 0.5);
}

.datastream-toolbar :deep(.v-field__clearable) {
  color: rgba(var(--v-theme-on-secondary), 0.9);
}

.datastream-search {
  max-width: 260px;
  min-width: 200px;
  flex: 0 1 260px;
}

@media (max-width: 1200px) {
  .datastream-toolbar__left {
    flex-direction: column;
    align-items: flex-start;
  }

  .datastream-search {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

.datastream-latest {
  display: flex;
  flex-direction: column;
  padding-top: 0;
}

.datastream-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.6rem;
}

.datastream-card {
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.datastream-card__content {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.datastream-card__title {
  font-weight: 600;
  font-size: 1rem;
}

.datastream-card__icons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.datastream-card__actions {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.datastream-card__meta-btn {
  align-self: flex-start;
}

.datastream-title {
  font-weight: 600;
  font-size: 1rem;
  max-width: 360px;
  overflow-wrap: anywhere;
}

.datastream-info-list,
.datastream-time-list {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding-top: 0;
}

.datastream-line {
  margin: 0;
  line-height: 1.3;
}

.datastream-id {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.datastream-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.datastream-actions__icons {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 32px;
  flex-wrap: wrap;
}

.datastream-download {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

@media (max-width: 960px) {
  .datastream-search {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

@media (max-width: 700px) {
  .datastream-toolbar__left,
  .datastream-toolbar__actions {
    width: 100%;
  }

  .datastream-toolbar__left {
    flex-direction: column;
    align-items: stretch;
  }

  .datastream-toolbar__actions {
    justify-content: flex-start;
  }

  .datastream-toolbar__actions :deep(.v-btn) {
    width: 100%;
    justify-content: center;
  }

  :deep(tbody .v-data-table__tr) {
    display: block;
    padding: 0.5rem 0;
  }

  :deep(tbody .v-data-table__td) {
    display: block;
    width: 100%;
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }

  :deep(tbody .v-data-table__td + .v-data-table__td) {
    border-top: 1px solid rgba(0, 0, 0, 0.08);
  }

  .datastream-info-list,
  .datastream-time-list {
    gap: 0.35rem;
  }

  .datastream-copy-btn {
    min-width: 40px;
    min-height: 40px;
  }
}

@media (min-width: 961px) {
  .datastream-info-list,
  .datastream-time-list {
    gap: 0.2rem;
  }
}
</style>
