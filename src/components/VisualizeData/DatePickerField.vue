<template>
  <div class="d-flex align-center gap-1" v-bind="$attrs">
    <v-text-field
      v-model="dateInput"
      v-maska="dateMaskOptions"
      @blur="handleDateBlur"
      placeholder="MM/DD/YYYY"
      append-inner-icon="mdi-calendar-blank"
      @click:append-inner="showDateDialog = true"
      hide-details
      density="compact"
    />

    <v-text-field
      v-model="timeInput"
      v-maska="timeMaskOptions"
      @blur="handleTimeBlur"
      placeholder="HH:MM"
      prepend-inner-icon="mdi-clock-outline"
      hide-details
      density="compact"
      style="max-width: 7rem"
    />
  </div>

  <v-dialog v-model="showDateDialog" max-width="22rem">
    <v-card>
      <v-card-title class="d-flex pt-4">
        Select {{ placeholder }}
        <v-spacer />
        <v-icon color="grey-darken-1" @click="showDateDialog = false">
          mdi-close
        </v-icon>
      </v-card-title>
      <v-divider />
      <v-date-picker
        hide-header
        v-model="pickerDate"
        @update:modelValue="onDatePicked"
      />
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { vMaska } from 'maska/vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: Date, required: true },
  placeholder: String,
})
const emit = defineEmits(['update:modelValue'])

const dateCompleted = ref(true)
const timeCompleted = ref(true)

const dateMaskOptions = {
  mask: '##/##/####',
  eager: true,
  onMaska: (detail: { completed: boolean }) => {
    dateCompleted.value = detail.completed
  },
}
const timeMaskOptions = {
  mask: '##:##',
  eager: true,
  onMaska: (detail: { completed: boolean }) => {
    timeCompleted.value = detail.completed
  },
}

const formatDateStr = (date: Date) => {
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${m}/${d}/${date.getFullYear()}`
}

const formatTimeStr = (date: Date) => {
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

const toMidnight = (date: Date) => {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

const showDateDialog = ref(false)

const dateInput = ref(formatDateStr(props.modelValue))
const timeInput = ref(formatTimeStr(props.modelValue))
const pickerDate = ref<Date>(toMidnight(props.modelValue))

watch(
  () => props.modelValue,
  (newValue) => {
    dateInput.value = formatDateStr(newValue)
    timeInput.value = formatTimeStr(newValue)
    pickerDate.value = toMidnight(newValue)
  }
)

const emitCombined = (date: Date, time: string) => {
  const [h, m] = time.split(':').map(Number)
  const result = new Date(date)
  result.setHours(h || 0, m || 0, 0, 0)
  emit('update:modelValue', result)
}

const onDatePicked = (date: Date) => {
  pickerDate.value = toMidnight(date)
  dateInput.value = formatDateStr(date)
  emitCombined(pickerDate.value, timeInput.value)
  showDateDialog.value = false
}

const handleDateBlur = () => {
  if (!dateCompleted.value) {
    dateInput.value = formatDateStr(pickerDate.value)
    return
  }
  const match = dateInput.value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (match) {
    const m = Math.max(1, Math.min(12, +match[1]!))
    const d = Math.max(1, Math.min(31, +match[2]!))
    const parsed = new Date(+match[3]!, m - 1, d)
    if (!isNaN(parsed.getTime())) {
      pickerDate.value = toMidnight(parsed)
      dateInput.value = formatDateStr(parsed)
      emitCombined(pickerDate.value, timeInput.value)
      return
    }
  }
  dateInput.value = formatDateStr(pickerDate.value)
}

const handleTimeBlur = () => {
  if (!timeCompleted.value) {
    timeInput.value = formatTimeStr(props.modelValue)
    return
  }
  const match = timeInput.value.match(/^(\d{2}):(\d{2})$/)
  if (match) {
    const h = Math.max(0, Math.min(23, +match[1]!))
    const m = Math.max(0, Math.min(59, +match[2]!))
    const time = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
    timeInput.value = time
    emitCombined(pickerDate.value, time)
    return
  }
  timeInput.value = formatTimeStr(props.modelValue)
}
</script>
