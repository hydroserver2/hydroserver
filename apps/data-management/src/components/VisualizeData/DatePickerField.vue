<template>
  <div>
    <v-text-field
      v-bind="$attrs"
      :placeholder="placeholder"
      v-model="inputDate"
      @blur="handleBlur"
      :append-inner-icon="mdiCalendarBlank"
      @click:append-inner="toggleDatePicker"
      hide-details
      density="compact"
      rounded="0"
      :color="resolvedColor"
      :base-color="resolvedColor"
      :bg-color="resolvedBgColor"
    />

    <v-dialog
      v-model="showDatePicker"
      max-width="32rem"
      content-class="date-picker-dialog"
    >
      <v-card class="date-picker-card" color="blue">
        <v-card-title class="d-flex pt-4">
          Select {{ placeholder }}
          <v-spacer />
          <v-icon
            :icon="mdiClose"
            color="white"
            @click="showDatePicker = false"
          />
        </v-card-title>
        <v-date-picker
          class="date-picker-body"
          hide-header
          v-model="localDate"
          @update:modelValue="dateSelected"
        />
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { mdiCalendarBlank, mdiClose } from '@mdi/js'
import { computed, ref, watch } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: Date, required: true },
  placeholder: String,
  color: String,
  active: Boolean,
})
const emit = defineEmits(['update:modelValue'])

const showDatePicker = ref(false)
const localDate = ref<Date>(props.modelValue)
const inputDate = ref(localDate.value.toLocaleDateString('en-US'))

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue !== localDate.value) {
      localDate.value = newValue
      inputDate.value = newValue.toLocaleDateString('en-US')
    }
  }
)

const dateSelected = (newDate: Date) => {
  localDate.value = newDate
  inputDate.value = newDate.toLocaleDateString('en-US')
  emit('update:modelValue', newDate)
  showDatePicker.value = false
}

const handleBlur = () => {
  if (inputDate.value === props.modelValue.toLocaleDateString('en-US')) return
  const parts = inputDate.value.split('/')
  try {
    const newDate = new Date(+parts[2], +parts[0] - 1, +parts[1])
    if (!isNaN(newDate.getTime())) {
      localDate.value = newDate
      emit('update:modelValue', newDate)
    } else {
      inputDate.value = localDate.value.toLocaleDateString('en-US')
    }
  } catch (e) {
    inputDate.value = localDate.value.toLocaleDateString('en-US')
  }
}

const toggleDatePicker = () => {
  showDatePicker.value = !showDatePicker.value
}

const resolvedColor = computed(() =>
  props.active ? props.color || 'primary' : undefined
)
const resolvedBgColor = computed(() =>
  props.active ? 'blue-lighten-5' : undefined
)
</script>

<style scoped>
.date-picker-card {
  overflow: hidden;
  border-radius: 0;
  width: 100%;
}

:deep(.date-picker-body) {
  width: 100%;
  border-radius: 0 !important;
}

.date-picker-dialog :deep(.v-overlay__content) {
  width: 100%;
  border-radius: 0;
}

:deep(.date-picker-body .v-date-picker__header),
:deep(.date-picker-body .v-date-picker-controls),
:deep(.date-picker-body .v-date-picker-month),
:deep(.date-picker-body .v-date-picker__title),
:deep(.date-picker-body .v-date-picker-month__day),
:deep(.date-picker-body .v-date-picker-month__day-button),
:deep(.date-picker-body .v-date-picker-month__weekday),
:deep(.date-picker-body .v-date-picker-month__week-number) {
  border-radius: 0 !important;
}

:deep(.date-picker-body .v-btn),
:deep(.date-picker-body .v-btn--rounded),
:deep(.date-picker-body .rounded-circle) {
  border-radius: 0 !important;
}

:deep(.date-picker-body .v-date-picker-month__day-btn) {
  --v-btn-height: 32px;
  --v-btn-size: 1rem;
  min-width: 32px;
}

.date-picker-divider {
  box-shadow: none !important;
}
</style>
