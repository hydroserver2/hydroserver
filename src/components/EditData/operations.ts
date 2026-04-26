import { markRaw, type Component } from 'vue'
import {
  EnumEditOperations,
  EnumFilterOperations,
} from '@uwrl/qc-utils'

import ValueThreshold from '@/components/FilterPoints/ValueThreshold.vue'
import DatetimeRange from '@/components/FilterPoints/DatetimeRange.vue'
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
    id: 'datetimeRange',
    title: 'Datetime range',
    description: 'Select points within a datetime range',
    icon: 'mdi-calendar-range',
    group: 'filter',
    requiresSelection: false,
    component: markRaw(DatetimeRange),
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
    id: 'qualifyingComments',
    title: 'Qualifying comments',
    description: 'Attach qualifier flags to selected points',
    icon: 'mdi-flag',
    group: 'add',
    requiresSelection: true,
    component: markRaw(QualifyingComments),
  },
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

/**
 * Map a `HistoryItem.method` (qc-utils enum value) to the matching
 * operation panel id, or `null` for system methods that have no
 * user-facing panel (SELECTION, ASSIGN_*_BULK).
 */
const methodToOperationId: Partial<Record<string, string>> = {
  [EnumFilterOperations.VALUE_THRESHOLD]: 'valueThreshold',
  [EnumFilterOperations.DATETIME_RANGE]: 'datetimeRange',
  [EnumFilterOperations.CHANGE]: 'change',
  [EnumFilterOperations.RATE_OF_CHANGE]: 'rateOfChange',
  [EnumFilterOperations.FIND_GAPS]: 'gaps',
  [EnumFilterOperations.PERSISTENCE]: 'persistence',
  [EnumEditOperations.DRIFT_CORRECTION]: 'driftCorrection',
  [EnumEditOperations.INTERPOLATE]: 'interpolate',
  [EnumEditOperations.CHANGE_VALUES]: 'changeValues',
  [EnumEditOperations.SHIFT_DATETIMES]: 'shiftDatetimes',
  [EnumEditOperations.DELETE_POINTS]: 'deletePoints',
  [EnumEditOperations.ADD_POINTS]: 'addPoints',
  [EnumEditOperations.FILL_GAPS]: 'fillGaps',
}

/**
 * Resolve a Material Design icon for a history entry's `method`.
 * Reuses the operation-panel icons where possible so history reads
 * with the same visual vocabulary as the edit drawer; falls back to
 * dedicated icons for system methods (SELECTION from a click/lasso,
 * bulk assign) which have no user-facing panel.
 */
export function iconForMethod(method: string): string {
  const opId = methodToOperationId[method]
  if (opId) {
    const op = operationsById[opId]
    if (op) return op.icon
  }
  if (method === EnumFilterOperations.SELECTION) {
    return 'mdi-cursor-default-click'
  }
  if (method === EnumEditOperations.ASSIGN_VALUES_BULK) return 'mdi-pencil'
  if (method === EnumEditOperations.ASSIGN_DATETIMES_BULK) {
    return 'mdi-calendar'
  }
  return 'mdi-circle-small'
}

/** Vuetify color tokens per operation group. Used by the edit drawer
 *  avatars and the history row icons so a method reads the same color
 *  in both places. */
export const colorForGroup: Record<OperationGroup, string> = {
  filter: 'primary',
  edit: 'primary',
  add: 'success',
}

/**
 * Resolve a Vuetify color for an operation, matching the EditDrawer
 * sidebar avatar logic exactly: edit ops that need a selection get
 * `warning`, everything else uses its group color.
 */
export function colorForOperation(op: OperationMeta): string {
  if (op.group === 'edit' && op.requiresSelection) return 'warning'
  return colorForGroup[op.group]
}

/**
 * Resolve a Vuetify color for a history entry's `method`. Same
 * per-item logic as the sidebar; SELECTION + bulk-assign system
 * methods fall back to grey since they have no panel.
 */
export function colorForMethod(method: string): string {
  const opId = methodToOperationId[method]
  if (opId) {
    const op = operationsById[opId]
    if (op) return colorForOperation(op)
  }
  return 'grey'
}
