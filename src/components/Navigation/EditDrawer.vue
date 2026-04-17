<template>
  <div class="edit-drawer d-flex flex-column">
    <div class="edit-drawer__header px-4 py-3">
      <div class="text-subtitle-2 font-weight-bold">Data Tools</div>
      <div class="text-caption text-medium-emphasis">
        Detect issues and edit observations
      </div>

      <div
        class="selection-banner mt-3 pa-2 pl-3 d-flex align-center"
        :class="{ 'selection-banner--active': hasSelection }"
      >
        <v-icon
          :icon="hasSelection ? 'mdi-checkbox-marked-circle' : 'mdi-selection-drag'"
          :color="hasSelection ? 'red' : 'grey'"
          size="22"
          class="mr-3"
        />
        <div class="flex-grow-1 d-flex flex-column">
          <div class="d-flex align-baseline gap-1">
            <span
              class="selection-banner__count text-h5 font-weight-bold"
              :class="hasSelection ? 'text-red' : 'text-medium-emphasis'"
            >
              {{ selectedData?.length ?? 0 }}
            </span>
            <span
              class="text-body-2 font-weight-medium"
              :class="hasSelection ? 'text-red' : 'text-medium-emphasis'"
            >
              point{{ selectedData?.length === 1 ? '' : 's' }} selected
            </span>
          </div>
          <div
            v-if="!hasSelection"
            class="text-caption text-medium-emphasis"
          >
            Box-select or click points on the plot
          </div>
        </div>
        <v-btn
          v-if="hasSelection"
          size="x-small"
          variant="text"
          color="red"
          icon="mdi-close"
          aria-label="Clear selection"
          @click="clearSelected"
        />
      </div>
    </div>

    <v-divider />

    <div class="edit-drawer__scroll flex-grow-1 overflow-y-auto">
      <v-list class="py-2" density="compact" nav lines="two">
        <v-list-subheader class="text-uppercase text-caption font-weight-bold">
          Filter Points
        </v-list-subheader>

        <v-list-item
          v-for="(item, i) in filterPoints"
          :key="`fp-${i}`"
          rounded="lg"
          class="mx-2 mb-1"
          @click="item.clickAction"
        >
          <template v-slot:prepend>
            <v-avatar size="32" color="primary" variant="flat">
              <v-icon size="18" color="white" :icon="item.props.prependIcon" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item>

        <v-list-subheader
          class="text-uppercase text-caption font-weight-bold mt-2"
        >
          Edit Data
        </v-list-subheader>

        <v-list-item
          v-for="(item, i) in editData"
          :key="`ed-${i}`"
          rounded="lg"
          class="mx-2 mb-1"
          :disabled="item.isDisabled?.()"
          @click="item.clickAction"
        >
          <template v-slot:prepend>
            <v-avatar
              size="32"
              :color="item.requiresSelection ? 'warning' : 'primary'"
              variant="flat"
            >
              <v-icon size="18" color="white" :icon="item.props.prependIcon" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ item.description }}
          </v-list-item-subtitle>
          <template
            v-if="item.requiresSelection && !selectedData?.length"
            v-slot:append
          >
            <v-tooltip location="start" text="Select points on the plot first">
              <template v-slot:activator="{ props: tooltipProps }">
                <v-icon
                  v-bind="tooltipProps"
                  size="14"
                  icon="mdi-information-outline"
                  class="text-medium-emphasis"
                />
              </template>
            </v-tooltip>
          </template>
        </v-list-item>
      </v-list>
    </div>
  </div>

  <!-- FILTER POINTS -->

  <v-dialog v-model="openValueThreshold" max-width="500">
    <ValueThreshold @close="openValueThreshold = false" />
  </v-dialog>

  <v-dialog v-model="openGaps" max-width="500">
    <Gaps @close="openGaps = false" />
  </v-dialog>

  <v-dialog v-model="openChange" max-width="500">
    <Change @close="openChange = false" />
  </v-dialog>

  <v-dialog v-model="openRateOfChange" max-width="500">
    <RateOfChange @close="openRateOfChange = false" />
  </v-dialog>

  <v-dialog v-model="openPersistence" max-width="500">
    <Persistence @close="openPersistence = false" />
  </v-dialog>

  <!-- EDIT DATA -->

  <v-dialog v-model="openChangeValues" max-width="500">
    <ChangeValues @close="openChangeValues = false" />
  </v-dialog>

  <v-dialog v-model="openShiftDatetimes" max-width="500">
    <ShiftDatetimes @close="openShiftDatetimes = false" />
  </v-dialog>

  <v-dialog v-model="openInterpolate" max-width="500">
    <Interpolate @close="openInterpolate = false" />
  </v-dialog>

  <v-dialog v-model="openDeletePoints" max-width="500">
    <DeletePoints @close="openDeletePoints = false" />
  </v-dialog>

  <v-dialog v-model="openDriftCorrection" max-width="700">
    <DriftCorrection @close="openDriftCorrection = false" />
  </v-dialog>

  <v-dialog v-model="openAddPoints" max-width="700">
    <AddPoints @close="openAddPoints = false" />
  </v-dialog>

  <v-dialog v-model="openFillGaps" max-width="700">
    <FillGaps @close="openFillGaps = false" />
  </v-dialog>

  <v-dialog v-model="openQualifyingComments" max-width="600">
    <QualifyingComments @close="openQualifyingComments = false" />
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDataSelection } from '@/composables/useDataSelection'

import ValueThreshold from '@/components/FilterPoints/ValueThreshold.vue'
import Change from '@/components/FilterPoints/Change.vue'
import RateOfChange from '@/components/FilterPoints/RateOfChange.vue'
import Persistence from '@/components/FilterPoints/Persistence.vue'
import Gaps from '@/components/FilterPoints/Gaps.vue'

import ChangeValues from '@/components/EditData/ChangeValues.vue'
import Interpolate from '@/components/EditData/Interpolate.vue'
import DeletePoints from '@/components/EditData/DeletePoints.vue'
import DriftCorrection from '@/components/EditData/DriftCorrection.vue'
import AddPoints from '@/components/EditData/AddPoints.vue'
import ShiftDatetimes from '@/components/EditData/ShiftDatetimes.vue'
import FillGaps from '@/components/EditData/FillGaps.vue'
import QualifyingComments from '@/components/EditData/QualifyingComments.vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'

// FILTER POINTS
const openValueThreshold = ref(false)
const openRateOfChange = ref(false)
const openChange = ref(false)
const openGaps = ref(false)
const openPersistence = ref(false)

// EDIT DATA
const openChangeValues = ref(false)
const openShiftDatetimes = ref(false)
const openInterpolate = ref(false)
const openDeletePoints = ref(false)
const openDriftCorrection = ref(false)
const openAddPoints = ref(false)
const openFillGaps = ref(false)
const openQualifyingComments = ref(false)

const filterPoints = [
  {
    title: 'Value thresholds',
    description: 'Flag points outside a min/max range',
    props: { prependIcon: 'mdi-align-vertical-center' },
    clickAction: () => (openValueThreshold.value = true),
  },
  {
    title: 'Change threshold',
    description: 'Flag abrupt changes between consecutive points',
    props: { prependIcon: 'mdi-swap-vertical' },
    clickAction: () => (openChange.value = true),
  },
  {
    title: 'Rate of change',
    description: 'Flag points by value change per unit time',
    props: { prependIcon: 'mdi-delta' },
    clickAction: () => (openRateOfChange.value = true),
  },
  {
    title: 'Find gaps',
    description: 'Locate time gaps larger than a threshold',
    props: { prependIcon: 'mdi-keyboard-space' },
    clickAction: () => (openGaps.value = true),
  },
  {
    title: 'Persistence',
    description: 'Flag runs of identical repeated values',
    props: { prependIcon: 'mdi-dots-horizontal' },
    clickAction: () => (openPersistence.value = true),
  },
]

const { selectedData } = storeToRefs(useDataVisStore())
const { clearSelected } = useDataSelection()
const hasSelection = computed(() => !!selectedData.value?.length)

const editData = [
  {
    title: 'Qualifying comments',
    description: 'Attach qualifier flags to selected points',
    props: { prependIcon: 'mdi-flag' },
    clickAction: () => (openQualifyingComments.value = true),
    isDisabled: () => !selectedData.value?.length,
    requiresSelection: true,
  },
  {
    title: 'Drift correction',
    description: 'Apply linear drift correction to a range',
    props: { prependIcon: 'mdi-chart-sankey' },
    clickAction: () => (openDriftCorrection.value = true),
    isDisabled: () => !selectedData.value?.length,
    requiresSelection: true,
  },
  {
    title: 'Interpolate',
    description: 'Fill selected points by interpolation',
    props: { prependIcon: 'mdi-transit-connection-horizontal' },
    clickAction: () => (openInterpolate.value = true),
    isDisabled: () => !selectedData.value?.length,
    requiresSelection: true,
  },
  {
    title: 'Change values',
    description: 'Set or offset values of selected points',
    props: { prependIcon: 'mdi-pencil' },
    clickAction: () => (openChangeValues.value = true),
    isDisabled: () => !selectedData.value?.length,
    requiresSelection: true,
  },
  {
    title: 'Shift datetimes',
    description: 'Shift timestamps of selected points',
    props: { prependIcon: 'mdi-calendar' },
    clickAction: () => (openShiftDatetimes.value = true),
    isDisabled: () => !selectedData.value?.length,
    requiresSelection: true,
  },
  {
    title: 'Delete points',
    description: 'Remove selected data points',
    props: { prependIcon: 'mdi-trash-can' },
    clickAction: () => (openDeletePoints.value = true),
    isDisabled: () => !selectedData.value?.length,
    requiresSelection: true,
  },
  {
    title: 'Add points',
    description: 'Insert new data points manually',
    props: { prependIcon: 'mdi-plus' },
    clickAction: () => (openAddPoints.value = true),
    requiresSelection: false,
  },
  {
    title: 'Fill gaps',
    description: 'Generate points in detected time gaps',
    props: { prependIcon: 'mdi-keyboard-space' },
    clickAction: () => (openFillGaps.value = true),
    requiresSelection: false,
  },
]
</script>

<style scoped>
.edit-drawer {
  height: 100%;
}

.edit-drawer__header {
  background-color: rgb(var(--v-theme-surface));
}

.edit-drawer__scroll {
  min-height: 0;
}

.selection-banner {
  border: 1px dashed rgba(var(--v-border-color), 0.35);
  border-radius: 8px;
  background-color: transparent;
  transition: background-color 150ms ease, border-color 150ms ease;
}

.selection-banner--active {
  border: 1px solid rgb(var(--v-theme-error));
  background-color: rgba(var(--v-theme-error), 0.08);
  box-shadow: 0 0 0 2px rgba(var(--v-theme-error), 0.12);
}

.selection-banner__count {
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

:deep(.v-list-item--disabled) {
  opacity: 0.55;
}
</style>
