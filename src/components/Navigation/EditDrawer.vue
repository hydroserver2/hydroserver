<template>
  <!-- <v-container>
      <v-expansion-panels color="primary-darken-2" v-model="panelOpen">
        <v-expansion-panel title="History" elevation="3">
          <v-expansion-panel-text>
            <v-virtual-scroll :items="['Action 3', 'Action 2', 'Action 1']">
              <template v-slot:default="{ item }">
                <v-list-item
                  :key="item"
                  @click="selected = item"
                  :class="{ 'v-list-item--active': selected === item }"
                  density="compact"
                  class="my-1"
                  rounded
                >
                  <v-list-item-title>{{ item }}</v-list-item-title>
                  <v-divider />
                </v-list-item>
              </template>
            </v-virtual-scroll>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-container> -->

  <v-divider />

  <v-list density="compact">
    <v-list-subheader>Filter points</v-list-subheader>

    <v-list-item
      v-for="(item, i) in filterPoints"
      :key="i"
      @click="item.clickAction"
    >
      <template v-slot:prepend>
        <v-icon :icon="item.props.prependIcon"></v-icon>
      </template>
      <v-list-item-title>{{ item.title }}</v-list-item-title>
    </v-list-item>
  </v-list>

  <v-divider />

  <v-list :items="editData" density="compact">
    <v-list-subheader>Edit Data</v-list-subheader>

    <v-list-item
      v-for="(item, i) in editData"
      :key="i"
      @click="item.clickAction"
      :disabled="item.isDisabled?.()"
    >
      <template v-slot:prepend>
        <v-icon :icon="item.props.prependIcon"></v-icon>
      </template>
      <v-list-item-title>{{ item.title }}</v-list-item-title>
    </v-list-item>
  </v-list>

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
    props: {
      prependIcon: 'mdi-align-vertical-center',
    },
    value: 1,
    clickAction: () => {
      openValueThreshold.value = true
    },
  },
  {
    title: 'Change Threshold',
    props: {
      prependIcon: 'mdi-swap-vertical',
    },
    clickAction: () => {
      openChange.value = true
    },
  },
  {
    title: 'Rate of change',
    props: {
      prependIcon: 'mdi-delta',
    },
    clickAction: () => {
      openRateOfChange.value = true
    },
  },
  {
    title: 'Find gaps',
    props: {
      prependIcon: 'mdi-keyboard-space',
    },
    clickAction: () => {
      openGaps.value = true
    },
  },
  {
    title: 'Persistence',
    props: {
      prependIcon: 'mdi-dots-horizontal',
    },
    clickAction: () => {
      openPersistence.value = true
    },
  },
]

const { selectedData } = storeToRefs(useDataVisStore())

const editData = [
  {
    title: 'Qualifying comments',
    props: {
      prependIcon: 'mdi-flag',
    },
    clickAction: () => {
      openQualifyingComments.value = true
    },
    isDisabled: () => !selectedData.value?.length,
  },
  {
    title: 'Drift correction',
    props: {
      prependIcon: 'mdi-chart-sankey',
    },
    clickAction: () => {
      openDriftCorrection.value = true
    },
    isDisabled: () => !selectedData.value?.length,
  },
  {
    title: 'Interpolate',
    props: {
      prependIcon: 'mdi-transit-connection-horizontal',
    },
    clickAction: () => (openInterpolate.value = true),
    isDisabled: () => !selectedData.value?.length,
  },
  {
    title: 'Change values',
    props: {
      prependIcon: 'mdi-pencil',
    },
    clickAction: () => (openChangeValues.value = true),
    isDisabled: () => !selectedData.value?.length,
  },
  {
    title: 'Shift Datetimes',
    props: {
      prependIcon: 'mdi-calendar',
    },
    clickAction: () => (openShiftDatetimes.value = true),
    isDisabled: () => !selectedData.value?.length,
  },
  {
    title: 'Delete points',
    props: {
      prependIcon: 'mdi-trash-can',
    },
    clickAction: () => {
      openDeletePoints.value = true
    },
    isDisabled: () => !selectedData.value?.length,
  },
  {
    title: 'Add points',
    props: {
      prependIcon: 'mdi-plus',
    },
    clickAction: () => {
      openAddPoints.value = true
    },
  },
  {
    title: 'Fill Gaps',
    props: {
      prependIcon: 'mdi-keyboard-space',
    },
    clickAction: () => {
      openFillGaps.value = true
    },
  },
]
</script>
