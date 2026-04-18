<template>
  <div class="edit-drawer d-flex flex-column fill-height">
    <div class="px-4 py-3 bg-surface">
      <div class="text-subtitle-2 font-weight-bold">Data Tools</div>
      <div class="text-caption text-medium-emphasis">
        Detect issues and edit observations
      </div>
    </div>

    <v-divider />

    <div class="flex-grow-1 overflow-y-auto" style="min-height: 0">
      <v-list class="py-2" density="compact" nav>
        <v-list-subheader class="text-uppercase text-caption font-weight-bold">
          Filter Data
        </v-list-subheader>

        <v-list-item
          v-for="(item, i) in filterPoints"
          :key="`fp-${i}`"
          rounded="lg"
          class="mb-1"
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
          class="mb-1"
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
        </v-list-item>

        <v-list-subheader
          class="text-uppercase text-caption font-weight-bold mt-2"
        >
          Add Data
        </v-list-subheader>

        <v-list-item
          v-for="(item, i) in addData"
          :key="`ad-${i}`"
          rounded="lg"
          class="mb-1"
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
import { ref } from 'vue'

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
]

const addData = [
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
/* The remaining rules all `:deep()` into Vuetify's v-list-item
   internals to allow text wrapping and reclaim padding inside a
   narrow (~220 px) drawer. No utility-class equivalents. */

/* Allow multi-line titles and descriptions instead of Vuetify's default
   single-line-with-ellipsis. Vuetify sets `overflow: hidden; text-overflow:
   ellipsis; white-space: nowrap` on these with high specificity (including
   variants like `.v-list-item--two-line .v-list-item-title`), and also
   applies `-webkit-line-clamp` via the `lines="two"` prop. We override
   with !important so the row can grow vertically for long descriptions. */
:deep(.v-list-item-title),
:deep(.v-list-item-subtitle) {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  -webkit-line-clamp: unset !important;
  line-clamp: unset !important;
  display: block !important;
  line-height: 1.3 !important;
  word-break: normal;
  overflow-wrap: anywhere;
}

/* Let the text column use the full available width inside the list
   item. Vuetify's default padding on `.v-list-item__content` and
   `.v-list-item` itself leaves ~10–12 px wasted on each side, which
   measurably narrows multi-line descriptions in a 220 px drawer. */
:deep(.v-list-item) {
  padding-inline: 10px !important;
}

:deep(.v-list-item__content) {
  overflow: visible !important;
  min-width: 0;
  flex: 1 1 100%;
}

:deep(.v-list-item__spacer) {
  width: 10px !important;
}

:deep(.v-list-item-subtitle) {
  opacity: 0.75;
}

/* Align the icon avatar to the top so it doesn't drift down next to
   two-line text blocks. */
:deep(.v-list-item__prepend) {
  align-self: flex-start;
  padding-top: 4px;
}

:deep(.v-list-item--disabled) {
  opacity: 0.55;
}
</style>
