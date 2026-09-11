<template>
  <div class="schedule-fields">
    <div class="schedule-heading">
      <h3 class="schedule-heading__title hs-title">Schedule</h3>
      <span class="schedule-heading__timezone hs-text-sm">{{
        timezoneLabel
      }}</span>
    </div>

    <v-checkbox
      v-model="enabled"
      color="primary"
      :disabled="disabled"
      label="Run this task on a schedule"
      hide-details
    />

    <div v-if="enabled" class="schedule-body">
      <div
        class="schedule-option"
        :class="{
          'schedule-option--selected': mode === 'interval',
          'schedule-option--disabled': disabled,
        }"
        tabindex="0"
        role="button"
        @click="selectMode('interval')"
        @keydown.enter.self.prevent="selectMode('interval')"
        @keydown.space.self.prevent="selectMode('interval')"
      >
        <div class="schedule-option__header">
          <span
            class="schedule-radio"
            :class="{ 'schedule-radio--selected': mode === 'interval' }"
          />
          <div
            class="schedule-option__title hs-title"
            :class="{ 'schedule-option__title--selected': mode === 'interval' }"
          >
            Repeating interval
          </div>
        </div>

        <div v-if="mode === 'interval'" class="schedule-option__controls">
          <span class="schedule-inline-label hs-text-sm">Every</span>
          <v-text-field
            v-model.number="interval"
            class="schedule-interval"
            type="number"
            min="1"
            hide-details
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
        @keydown.enter.self.prevent="selectMode('crontab')"
        @keydown.space.self.prevent="selectMode('crontab')"
      >
        <div class="schedule-option__header">
          <span
            class="schedule-radio"
            :class="{ 'schedule-radio--selected': mode === 'crontab' }"
          />
          <div
            class="schedule-option__title hs-title"
            :class="{ 'schedule-option__title--selected': mode === 'crontab' }"
          >
            Crontab expression
          </div>
        </div>

        <div v-if="mode === 'crontab'" class="schedule-option__controls">
          <v-text-field
            v-model="crontab"
            class="schedule-crontab hs-font-data"
            placeholder="0 9 * * *"
            hide-details
            :rules="rules.required"
            :disabled="disabled"
          />
        </div>
      </div>

      <div class="schedule-start-row">
        <label class="schedule-start-label hs-text-sm" for="task-start-time"
          >Start</label
        >
        <v-text-field
          id="task-start-time"
          v-model="startInput"
          class="schedule-start-input"
          type="datetime-local"
          hide-details
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
  }>(),
  {
    disabled: false,
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

watch([enabled, mode, interval, intervalPeriod, crontab, startTime], () => {
  if (!hydrating.value) emit('update:modelValue', buildSchedule())
})

watch(enabled, (next) => {
  if (next && !startTime.value) startTime.value = new Date().toISOString()
})
</script>

<style scoped>
.schedule-fields {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-16);
  width: 100%;
}

.schedule-heading {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-8);
  align-items: baseline;
}

.schedule-heading__title {
  color: var(--hs-text-secondary);
}

.schedule-heading__timezone {
  color: var(--hs-text-secondary);
  line-height: 1.3;
}

/*
 * Two option cards side by side, with the start row spanning both. `auto-fit`
 * can't be used here: the spanning row keeps every track occupied, so the
 * cards would stay pinned at the minimum column width however wide the form
 * gets.
 */
.schedule-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--hs-space-12);
}

.schedule-option {
  min-height: 92px;
  padding: var(--hs-space-12);
  outline: none;
  background: var(--hs-surface);
  border: 1px solid var(--hs-input-border);
  border-radius: var(--hs-radius-md);
  cursor: pointer;
  transition:
    border-color 160ms ease-in-out,
    background-color 160ms ease-in-out,
    box-shadow 160ms ease-in-out;
}

.schedule-option:hover,
.schedule-option:focus-visible {
  border-color: var(--hs-primary);
}

.schedule-option--selected {
  background: color-mix(in srgb, var(--hs-primary) 8%, var(--hs-surface));
  border-color: var(--hs-primary);
  border-width: 2px;
  box-shadow: inset 0 0 0 1px
    color-mix(in srgb, var(--hs-primary) 8%, transparent);
}

.schedule-option--disabled {
  opacity: 0.72;
  cursor: default;
}

.schedule-option__header {
  display: flex;
  gap: var(--hs-space-8);
  align-items: flex-start;
}

.schedule-radio {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  margin-top: var(--hs-space-2);
  border: 2px solid var(--hs-text-secondary);
  /* A perfect circle is a shape, not a step on the radius scale. */
  border-radius: 50%;
}

.schedule-radio--selected {
  background: var(--hs-surface);
  border-color: var(--hs-primary);
  box-shadow: inset 0 0 0 3px var(--hs-primary);
}

.schedule-option__title {
  color: var(--hs-text-primary);
  line-height: 1.2;
}

.schedule-option__title--selected {
  color: var(--hs-primary);
}

.schedule-option__controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-8);
  align-items: center;
  margin-top: var(--hs-space-12);
  padding-left: var(--hs-space-24);
}

.schedule-inline-label,
.schedule-start-label {
  color: var(--hs-text-primary);
  font-weight: var(--hs-font-weight-medium);
}

.schedule-interval {
  flex: 0 0 80px;
  max-width: 80px;
}

/* Wide enough for the longest unit ("Minutes") to render untruncated. */
.schedule-unit {
  flex: 0 0 120px;
  max-width: 120px;
}

.schedule-crontab {
  flex: 1 1 220px;
  min-width: 0;
  width: 100%;
}

.schedule-start-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-8);
  align-items: center;
  grid-column: 1 / -1;
}

.schedule-start-input {
  flex: 0 1 250px;
  min-width: 220px;
  max-width: 250px;
}

@media (max-width: 700px) {
  .schedule-body {
    grid-template-columns: 1fr;
  }

  .schedule-option__controls {
    padding-left: 0;
  }

  .schedule-start-input {
    width: 100%;
    max-width: none;
  }
}
</style>
