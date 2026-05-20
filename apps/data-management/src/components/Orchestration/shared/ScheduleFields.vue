<template>
  <div class="schedule-fields">
    <div class="schedule-heading mb-2">
      <div class="section-heading">Schedule</div>
      <span class="timezone-label">{{ timezoneLabel }}</span>
    </div>

    <v-switch
      v-model="enabled"
      :color="color"
      density="compact"
      hide-details
      :disabled="disabled"
      label="Run this task on a schedule"
      class="mb-2"
    />

    <div v-if="enabled" class="schedule-body mb-4">
      <div
        class="schedule-option"
        :class="{
          'schedule-option--selected': mode === 'interval',
          'schedule-option--disabled': disabled,
        }"
        tabindex="0"
        role="button"
        @click="selectMode('interval')"
        @keydown.enter.prevent="selectMode('interval')"
        @keydown.space.prevent="selectMode('interval')"
      >
        <div class="schedule-option__header">
          <span
            class="schedule-radio"
            :class="{ 'schedule-radio--selected': mode === 'interval' }"
          />
          <div
            class="schedule-option__title"
            :class="{ 'schedule-option__title--selected': mode === 'interval' }"
          >
            Repeating interval
          </div>
        </div>

        <div v-if="mode === 'interval'" class="schedule-option__controls">
          <span class="schedule-inline-label">Every</span>
          <v-text-field
            v-model.number="interval"
            class="schedule-interval"
            type="number"
            min="1"
            hide-details
            variant="outlined"
            rounded="lg"
            density="compact"
            :rules="[...rules.required, positiveInteger]"
            :disabled="disabled"
          />
          <v-select
            v-model="intervalPeriod"
            class="schedule-unit"
            :items="scheduleUnitOptions"
            item-title="title"
            item-value="value"
            hide-details
            variant="outlined"
            rounded="lg"
            density="compact"
            :rules="rules.required"
            :disabled="disabled"
          />
        </div>
      </div>

      <div
        class="schedule-option"
        :class="{
          'schedule-option--selected': mode === 'crontab',
          'schedule-option--disabled': disabled,
        }"
        tabindex="0"
        role="button"
        @click="selectMode('crontab')"
        @keydown.enter.prevent="selectMode('crontab')"
        @keydown.space.prevent="selectMode('crontab')"
      >
        <div class="schedule-option__header">
          <span
            class="schedule-radio"
            :class="{ 'schedule-radio--selected': mode === 'crontab' }"
          />
          <div
            class="schedule-option__title"
            :class="{ 'schedule-option__title--selected': mode === 'crontab' }"
          >
            Crontab expression
          </div>
        </div>

        <div v-if="mode === 'crontab'" class="schedule-option__controls">
          <v-text-field
            v-model="crontab"
            class="schedule-crontab"
            placeholder="0 9 * * *"
            hide-details
            variant="outlined"
            rounded="lg"
            density="compact"
            :rules="rules.required"
            :disabled="disabled"
          />
        </div>
      </div>

      <div class="schedule-start-row">
        <label class="schedule-start-label" for="task-start-time">Start</label>
        <v-text-field
          id="task-start-time"
          v-model="startInput"
          class="schedule-start-input"
          type="datetime-local"
          hide-details
          variant="outlined"
          rounded="lg"
          density="compact"
          :disabled="disabled"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { IntervalPeriod, TaskSchedule } from '@hydroserver/client'
import { getLocalTimeZone, inputToIso, isoToInput } from '@/utils/time'
import { rules } from '@/utils/rules'

const props = withDefaults(
  defineProps<{
    modelValue: TaskSchedule | null
    disabled?: boolean
    color?: string
  }>(),
  {
    disabled: false,
    color: 'primary',
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: TaskSchedule | null): void
}>()

const enabled = ref(false)
const mode = ref<'interval' | 'crontab'>('interval')
const interval = ref<number | null>(1)
const intervalPeriod = ref<IntervalPeriod>('days')
const crontab = ref('')
const startTime = ref<string | null>(new Date().toISOString())
const hydrating = ref(false)
const timezoneLabel = getLocalTimeZone()

const scheduleUnitOptions: { title: string; value: IntervalPeriod }[] = [
  { title: 'Minutes', value: 'minutes' },
  { title: 'Hours', value: 'hours' },
  { title: 'Days', value: 'days' },
]

type Rule = (v: any) => true | string

const positiveInteger: Rule = (value) =>
  (Number.isInteger(Number(value)) && Number(value) >= 1) ||
  'Must be a positive whole number.'

const startInput = computed({
  get: () => isoToInput(startTime.value),
  set: (value: string) => {
    startTime.value = value ? inputToIso(value) : null
  },
})

function selectMode(nextMode: 'interval' | 'crontab') {
  if (props.disabled) return
  mode.value = nextMode
}

function hydrate(schedule: TaskSchedule | null | undefined) {
  hydrating.value = true
  if (!schedule) {
    enabled.value = false
    mode.value = 'interval'
    interval.value = 1
    intervalPeriod.value = 'days'
    crontab.value = ''
    startTime.value = new Date().toISOString()
  } else {
    enabled.value = true
    mode.value = schedule.crontab !== null ? 'crontab' : 'interval'
    interval.value = schedule.interval ?? 1
    intervalPeriod.value = schedule.intervalPeriod ?? 'days'
    crontab.value = schedule.crontab ?? ''
    startTime.value = schedule.startTime ?? new Date().toISOString()
  }
  hydrating.value = false
}

function buildSchedule(): TaskSchedule | null {
  if (!enabled.value) return null
  if (mode.value === 'crontab') {
    return {
      enabled: true,
      startTime: startTime.value,
      nextRunAt: null,
      crontab: crontab.value.trim(),
      interval: null,
      intervalPeriod: null,
    }
  }

  return {
    enabled: true,
    startTime: startTime.value,
    nextRunAt: null,
    crontab: null,
    interval: interval.value,
    intervalPeriod: intervalPeriod.value,
  }
}

watch(
  () => props.modelValue,
  (schedule) => hydrate(schedule),
  { immediate: true }
)

watch(
  [enabled, mode, interval, intervalPeriod, crontab, startTime],
  () => {
    if (!hydrating.value) emit('update:modelValue', buildSchedule())
  }
)

watch(enabled, (next) => {
  if (next && !startTime.value) startTime.value = new Date().toISOString()
})
</script>

<style scoped>
.schedule-fields {
  width: 100%;
}

.schedule-heading {
  align-items: baseline;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.section-heading {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
}

.timezone-label {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-size: 0.78rem;
  font-weight: 500;
  line-height: 1.3;
}

.schedule-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.schedule-option {
  background: #fff;
  border: 1px solid #d0c9d8;
  border-radius: 8px;
  cursor: pointer;
  min-height: 92px;
  outline: none;
  padding: 12px;
  transition: border-color 160ms ease-in-out, background-color 160ms ease-in-out,
    box-shadow 160ms ease-in-out;
}

.schedule-option:hover,
.schedule-option:focus-visible {
  border-color: v-bind(color);
}

.schedule-option--selected {
  background: color-mix(in srgb, v-bind(color) 8%, white);
  border-color: v-bind(color);
  border-width: 2px;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, v-bind(color) 8%, transparent);
}

.schedule-option--disabled {
  cursor: default;
  opacity: 0.72;
}

.schedule-option__header {
  align-items: flex-start;
  display: flex;
  gap: 8px;
}

.schedule-radio {
  border: 2px solid #7e7886;
  border-radius: 50%;
  flex: 0 0 auto;
  height: 16px;
  margin-top: 1px;
  width: 16px;
}

.schedule-radio--selected {
  background: #fff;
  border-color: v-bind(color);
  box-shadow: inset 0 0 0 3px v-bind(color);
}

.schedule-option__title {
  color: #1f1d24;
  font-size: 0.86rem;
  font-weight: 700;
  line-height: 1.2;
}

.schedule-option__title--selected {
  color: v-bind(color);
}

.schedule-option__controls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-left: 24px;
}

.schedule-inline-label,
.schedule-start-label {
  color: #1f1d24;
  font-size: 0.82rem;
  font-weight: 500;
}

.schedule-interval {
  flex: 0 0 80px;
  max-width: 80px;
}

.schedule-unit {
  flex: 0 0 112px;
  max-width: 112px;
}

.schedule-crontab {
  flex: 1 1 220px;
  min-width: 0;
  width: 100%;
}

.schedule-start-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  grid-column: 1 / -1;
}

.schedule-start-input {
  flex: 0 1 250px;
  max-width: 250px;
  min-width: 220px;
}

@media (max-width: 700px) {
  .schedule-body {
    grid-template-columns: 1fr;
  }

  .schedule-option__controls {
    padding-left: 0;
  }

  .schedule-start-input {
    max-width: none;
    width: 100%;
  }
}
</style>
