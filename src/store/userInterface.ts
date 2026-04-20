import { LogicalOperation, Operator, TimeUnit } from '@uwrl/qc-utils'
import { defineStore } from 'pinia'
import { ref } from 'vue'

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
    logicalComparators,
    selectedRateOfChangeComparator,
    rateOfChangeValue,
    selectedChangeComparator,
    changeValue,
  }
})
