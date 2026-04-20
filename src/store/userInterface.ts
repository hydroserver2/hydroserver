import { LogicalOperation, Operator, TimeUnit } from '@uwrl/qc-utils'
import { defineStore, storeToRefs } from 'pinia'
import { ref, watch } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { loadOpParams } from '@/composables/useOperationParams'

/**
 * Map the datastream's `intendedTimeSpacingUnit` (plural English words
 * stored on the server) to the `TimeUnit` enum key used by the gap /
 * fill / shift selectors in this app (`SECOND`, `MINUTE`, `HOUR`,
 * `DAY`). Returns `null` for unrecognised or missing units so callers
 * can leave the user's previous default untouched.
 */
export const timeSpacingUnitToTimeUnitKey = (
  unit: string | null | undefined
): string | null => {
  switch (unit) {
    case 'seconds':
      return 'SECOND'
    case 'minutes':
      return 'MINUTE'
    case 'hours':
      return 'HOUR'
    case 'days':
      return 'DAY'
    default:
      return null
  }
}

export enum InterpolationMethods {
  LINEAR = 'LINEAR',
}

export enum DriftCorrectionMethods {
  LINEAR = 'LINEAR',
}

export enum DrawerType {
  Edit = 'Edit',
  Select = 'Select',
  None = '',
}

type View = DrawerType.Edit | DrawerType.Select

export const useUIStore = defineStore('userInterface', () => {
  // Navigation Drawer
  const selectedDrawer = ref<DrawerType>(DrawerType.Select)
  const isDrawerOpen = ref(true)

  // View
  const currentView = ref<View>(DrawerType.Select)

  // Operation panel — which operation's details are shown in the right
  // sidebar below the edit history. `null` means no panel is open.
  const selectedOperation = ref<string | null>(null)

  // Selection view content
  const cardHeight = ref(40)
  const tableHeight = ref(35)

  const onRailItemClicked = (title: DrawerType) => {
    if (selectedDrawer.value === title) {
      isDrawerOpen.value = !isDrawerOpen.value
    } else {
      selectedDrawer.value = title
      if (title === DrawerType.Edit) currentView.value = DrawerType.Edit
      if (title === DrawerType.Select) currentView.value = DrawerType.Select
      isDrawerOpen.value = true
    }
  }

  // Change Values
  const operators = [...Object.keys(Operator)]
  const selectedOperator = ref(0)
  const operationValue = ref(0.1)

  // GAP ANALYSYS
  const interpolateValues = ref(false)
  const selectedInterpolationMethod = ref(InterpolationMethods.LINEAR)
  const gapUnits = ref([...Object.keys(TimeUnit)])
  const selectedGapUnit = ref(gapUnits.value[1])
  const gapAmount = ref(15)

  // FILL
  const fillUnits = ref([...Object.keys(TimeUnit)])
  const selectedFillUnit = ref(fillUnits.value[1])
  const fillAmount = ref(15)
  // Sentinel written into filled datetimes when `interpolateValues` is
  // off. Default tracks the QC datastream's declared `noDataValue` (see
  // the watcher below) so users don't have to re-type it each session.
  const noDataValue = ref(-9999)

  // Seed gap / fill defaults when the QC datastream changes. Preference
  // order:
  //   1. Per-datastream persisted values (user's last commit for this
  //      series) — so reopening a panel feels continuous.
  //   2. Datastream's declared `intendedTimeSpacing` /
  //      `intendedTimeSpacingUnit` / `noDataValue` — a reasonable
  //      starting point for first-time use.
  //   3. Current ref values — keep whatever the user had if the
  //      datastream lacks metadata.
  // A null change (unset) is skipped so closing and reopening the QC
  // drawer without a datastream loaded doesn't clobber form state.
  const { qcDatastream } = storeToRefs(useDataVisStore())
  watch(
    qcDatastream,
    (ds) => {
      if (!ds) return
      const persisted = loadOpParams(ds.id)

      const spacing = Number(
        (ds as { intendedTimeSpacing?: number }).intendedTimeSpacing
      )
      const unitKey = timeSpacingUnitToTimeUnitKey(
        (ds as { intendedTimeSpacingUnit?: string | null })
          .intendedTimeSpacingUnit
      )
      const cadenceKnown =
        Number.isFinite(spacing) && spacing > 0 && unitKey != null

      gapAmount.value =
        persisted?.gapAmount ?? (cadenceKnown ? spacing : gapAmount.value)
      selectedGapUnit.value =
        persisted?.gapUnit ?? (cadenceKnown ? unitKey! : selectedGapUnit.value)
      fillAmount.value =
        persisted?.fillAmount ?? (cadenceKnown ? spacing : fillAmount.value)
      selectedFillUnit.value =
        persisted?.fillUnit ??
        (cadenceKnown ? unitKey! : selectedFillUnit.value)

      const nd = Number((ds as { noDataValue?: number }).noDataValue)
      noDataValue.value =
        persisted?.noDataValue ??
        (Number.isFinite(nd) ? nd : noDataValue.value)
    },
    { immediate: true }
  )

  // DRIFT CORRECTION
  const selectedDriftCorrectionMethod = ref(DriftCorrectionMethods.LINEAR)
  const driftGapWidth = ref(1)

  // SHIFT VALUES
  const shiftUnits = ref([...Object.keys(TimeUnit)])
  const selectedShiftUnit = ref(shiftUnits.value[1])
  const shiftAmount = ref(15)

  // RATE OF CHANGE
  const logicalComparators = [
    ...Object.keys(LogicalOperation).map((key) => ({
      value: key,
      // @ts-ignore
      title: LogicalOperation[key],
    })),
  ]
  const selectedRateOfChangeComparator = ref(logicalComparators[2])
  const rateOfChangeValue = ref(0)

  // CHANGE
  const selectedChangeComparator = ref(logicalComparators[2])
  const changeValue = ref(0)

  return {
    selectedDrawer,
    isDrawerOpen,
    currentView,
    selectedOperation,
    cardHeight,
    tableHeight,
    onRailItemClicked,
    shiftUnits,
    selectedShiftUnit,
    shiftAmount,
    selectedInterpolationMethod,
    driftGapWidth,
    selectedDriftCorrectionMethod,
    operators,
    selectedOperator,
    operationValue,
    interpolateValues,
    selectedGapUnit,
    gapAmount,
    gapUnits,
    selectedFillUnit,
    fillAmount,
    fillUnits,
    noDataValue,
    logicalComparators,
    selectedRateOfChangeComparator,
    rateOfChangeValue,
    selectedChangeComparator,
    changeValue,
  }
})
