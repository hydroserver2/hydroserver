<template>
  <div class="task-form-section">
    <div class="task-form-section-header">
      <h3 class="task-form-section-title">Schedule</h3>
      <span class="task-form-section-subtitle">{{ timezoneLabel }}</span>
    </div>

    <div class="schedule-card-grid">
      <div
        class="schedule-card"
        :class="{ 'schedule-card-active': scheduleMode === 'interval' }"
        tabindex="0"
        role="button"
        @click="scheduleMode = 'interval'"
        @keydown.enter.prevent="scheduleMode = 'interval'"
        @keydown.space.prevent="scheduleMode = 'interval'"
      >
        <div class="schedule-card-top">
          <span
            class="schedule-card-radio"
            :class="{
              'schedule-card-radio-active': scheduleMode === 'interval',
            }"
          />
          <div>
            <div class="schedule-card-title">Repeating interval</div>
          </div>
        </div>

        <div v-if="scheduleMode === 'interval'" class="schedule-card-body">
          <span class="schedule-inline-label">Every</span>
          <v-text-field
            v-model.number="task.schedule!.interval"
            class="max-w-20"
            type="number"
            min="1"
            hide-details
            variant="outlined"
            rounded="lg"
            :rules="[(v) => !!v || 'Interval is required']"
          />
          <v-select
            v-model="task.schedule!.intervalPeriod"
            class="schedule-unit-select"
            :items="intervalUnitOptions"
            item-title="title"
            item-value="value"
            hide-details
            variant="outlined"
            density="compact"
            rounded="lg"
            :rules="[(v) => !!v || 'Units are required']"
          />
        </div>
      </div>

      <div
        class="schedule-card"
        :class="{ 'schedule-card-active': scheduleMode === 'crontab' }"
        tabindex="0"
        role="button"
        @click="scheduleMode = 'crontab'"
        @keydown.enter.prevent="scheduleMode = 'crontab'"
        @keydown.space.prevent="scheduleMode = 'crontab'"
      >
        <div class="schedule-card-top">
          <span
            class="schedule-card-radio"
            :class="{
              'schedule-card-radio-active': scheduleMode === 'crontab',
            }"
          />
          <div>
            <div class="schedule-card-title">Crontab expression</div>
            <div class="schedule-card-copy">Advanced cron syntax</div>
          </div>
        </div>

        <div v-if="scheduleMode === 'crontab'" class="schedule-card-body">
          <v-text-field
            v-model="task.schedule!.crontab"
            class="schedule-crontab-input schedule-crontab-input-inline"
            placeholder="0 9 * * *"
            hide-details
            variant="outlined"
            rounded="lg"
            density="compact"
          />
        </div>
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
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Task, TaskSchedule } from '@hydroserver/client'
import { computed, ref } from 'vue'

const task = defineModel<Task>('task', { required: true })

const scheduleMode = ref<'interval' | 'crontab'>(
  task.value.schedule?.crontab ? 'crontab' : 'interval'
)

const timezoneLabel = Intl.DateTimeFormat().resolvedOptions().timeZone

const intervalUnitOptions = [
  { value: 'minutes', title: 'Minutes' },
  { value: 'hours', title: 'Hours' },
  { value: 'days', title: 'Days' },
] as const

function defaultSchedule(): TaskSchedule {
  return {
    enabled: true,
    startTime: new Date().toISOString(),
    nextRunAt: null,
    crontab: null,
    interval: 1,
    intervalPeriod: 'days',
  }
}

function ensureIsoUtc(s: string | null = ''): string | null {
  return s && !/([Zz]|[+-]\d{2}:\d{2})$/.test(s) ? s + 'Z' : s
}

function isoToInput(iso: string | null = ''): string {
  if (!iso) return ''
  const normalized = ensureIsoUtc(iso) ?? ''
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return ''
  const tzOffsetMs = d.getTimezoneOffset() * 60_000
  const local = new Date(d.getTime() - tzOffsetMs)
  return local.toISOString().slice(0, 16)
}

function inputToIso(str = ''): string {
  if (!str) return ''
  const parsed = new Date(str)
  return parsed.toISOString()
}

const startInput = computed({
  get: () => isoToInput(task.value.schedule?.startTime ?? ''),
  set: (v: string) => {
    if (!task.value.schedule) task.value.schedule = defaultSchedule()
    task.value.schedule.startTime = v ? inputToIso(v) : null
  },
})
</script>

<style scoped>
.task-form-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.task-form-section-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.task-form-section-title {
  font-size: 0.67rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #4f4b59;
}
.task-form-section-subtitle {
  color: #5f5a67;
  font-size: 0.72rem;
  line-height: 1.3;
}
.schedule-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px;
}
.schedule-card {
  border: 2px solid #d0c9d8;
  border-radius: 14px;
  background: #fff;
  padding: 8px 10px;
  transition: border-color 0.16s ease, background-color 0.16s ease,
    box-shadow 0.16s ease;
  outline: none;
}
.schedule-card:hover,
.schedule-card:focus-visible {
  border-color: #1565c0;
}
.schedule-card-active {
  border-color: #1565c0;
  background: #edf3ff;
  box-shadow: inset 0 0 0 1px rgba(21, 101, 192, 0.05);
}
.schedule-card-top {
  display: flex;
  align-items: flex-start;
  gap: 5px;
}
.schedule-card-radio {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid #7e7886;
  flex-shrink: 0;
  margin-top: 1px;
}
.schedule-card-radio-active {
  border-color: #1565c0;
  box-shadow: inset 0 0 0 3px #1565c0;
  background: #fff;
}
.schedule-card-title {
  font-size: 0.79rem;
  font-weight: 700;
  color: #1f1d24;
  line-height: 1.2;
}
.schedule-card-copy {
  margin-top: 1px;
  color: #5f5a67;
  font-size: 0.68rem;
  line-height: 1.25;
}
.schedule-card-body {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
  padding-left: 28px;
  flex-wrap: wrap;
}
.schedule-inline-label,
.schedule-start-label {
  font-size: 0.74rem;
  font-weight: 500;
  color: #1f1d24;
}
:deep(.schedule-interval-input input[type='number']) {
  appearance: textfield;
  -moz-appearance: textfield;
}
:deep(.schedule-interval-input input[type='number']::-webkit-inner-spin-button),
:deep(
    .schedule-interval-input input[type='number']::-webkit-outer-spin-button
  ) {
  -webkit-appearance: none;
  margin: 0;
}
.schedule-unit-select {
  max-width: 110px;
}
.schedule-crontab-input {
  max-width: 280px;
}
.schedule-crontab-input-inline {
  width: 100%;
  max-width: 100%;
}
.schedule-start-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.schedule-start-input {
  max-width: 220px;
}
.schedule-card-active :deep(.v-field) {
  background: #ffffff;
}
.schedule-card-active :deep(.v-field__overlay) {
  background: transparent;
}
.schedule-card-active :deep(.v-field__outline) {
  --v-field-border-opacity: 1;
}
:deep(.schedule-start-input .v-field__input) {
  align-items: center;
}
:deep(.schedule-start-input input[type='datetime-local']) {
  line-height: 1;
  padding-right: 2px;
}
:deep(
    .schedule-start-input
      input[type='datetime-local']::-webkit-calendar-picker-indicator
  ) {
  margin: 0;
  padding: 0;
  opacity: 0.82;
  transform: translateY(-1px);
}
@media (max-width: 900px) {
  .schedule-card-body {
    padding-left: 0;
  }
}
@media (max-width: 640px) {
  .schedule-start-input,
  .schedule-crontab-input {
    max-width: 100%;
    width: 100%;
  }
}
</style>
