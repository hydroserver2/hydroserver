import { markRaw, type Component } from 'vue'

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

export type OperationGroup = 'filter' | 'edit' | 'add'

export interface OperationMeta {
  id: string
  title: string
  description: string
  icon: string
  group: OperationGroup
  /** When true, the operation acts on a user point selection and is
   *  disabled in the drawer until the user has selected points. */
  requiresSelection: boolean
  component: Component
}

export const operations: OperationMeta[] = [
  // Filter Data
  {
    id: 'valueThreshold',
    title: 'Value thresholds',
    description: 'Flag points outside a min/max range',
    icon: 'mdi-align-vertical-center',
    group: 'filter',
    requiresSelection: false,
    component: markRaw(ValueThreshold),
  },
  {
    id: 'change',
    title: 'Change threshold',
    description: 'Flag abrupt changes between consecutive points',
    icon: 'mdi-swap-vertical',
    group: 'filter',
    requiresSelection: false,
    component: markRaw(Change),
  },
  {
    id: 'rateOfChange',
    title: 'Rate of change',
    description: 'Flag points by value change per unit time',
    icon: 'mdi-delta',
    group: 'filter',
    requiresSelection: false,
    component: markRaw(RateOfChange),
  },
  {
    id: 'gaps',
    title: 'Find gaps',
    description: 'Locate time gaps larger than a threshold',
    icon: 'mdi-keyboard-space',
    group: 'filter',
    requiresSelection: false,
    component: markRaw(Gaps),
  },
  {
    id: 'persistence',
    title: 'Persistence',
    description: 'Flag runs of identical repeated values',
    icon: 'mdi-dots-horizontal',
    group: 'filter',
    requiresSelection: false,
    component: markRaw(Persistence),
  },
  // Edit Data
  {
    id: 'qualifyingComments',
    title: 'Qualifying comments',
    description: 'Attach qualifier flags to selected points',
    icon: 'mdi-flag',
    group: 'edit',
    requiresSelection: true,
    component: markRaw(QualifyingComments),
  },
  {
    id: 'driftCorrection',
    title: 'Drift correction',
    description: 'Apply linear drift correction to a range',
    icon: 'mdi-chart-sankey',
    group: 'edit',
    requiresSelection: true,
    component: markRaw(DriftCorrection),
  },
  {
    id: 'interpolate',
    title: 'Interpolate',
    description: 'Fill selected points by interpolation',
    icon: 'mdi-transit-connection-horizontal',
    group: 'edit',
    requiresSelection: true,
    component: markRaw(Interpolate),
  },
  {
    id: 'changeValues',
    title: 'Change values',
    description: 'Set or offset values of selected points',
    icon: 'mdi-pencil',
    group: 'edit',
    requiresSelection: true,
    component: markRaw(ChangeValues),
  },
  {
    id: 'shiftDatetimes',
    title: 'Shift datetimes',
    description: 'Shift timestamps of selected points',
    icon: 'mdi-calendar',
    group: 'edit',
    requiresSelection: true,
    component: markRaw(ShiftDatetimes),
  },
  {
    id: 'deletePoints',
    title: 'Delete points',
    description: 'Remove selected data points',
    icon: 'mdi-trash-can',
    group: 'edit',
    requiresSelection: true,
    component: markRaw(DeletePoints),
  },
  // Add Data
  {
    id: 'addPoints',
    title: 'Add points',
    description: 'Insert new data points manually',
    icon: 'mdi-plus',
    group: 'add',
    requiresSelection: false,
    component: markRaw(AddPoints),
  },
  {
    id: 'fillGaps',
    title: 'Fill gaps',
    description: 'Generate points in detected time gaps',
    icon: 'mdi-keyboard-space',
    group: 'add',
    requiresSelection: false,
    component: markRaw(FillGaps),
  },
]

export const operationsById: Record<string, OperationMeta> =
  Object.fromEntries(operations.map((op) => [op.id, op]))

export const operationsByGroup = {
  filter: operations.filter((o) => o.group === 'filter'),
  edit: operations.filter((o) => o.group === 'edit'),
  add: operations.filter((o) => o.group === 'add'),
}
