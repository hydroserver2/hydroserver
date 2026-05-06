<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex items-baseline gap-1.5">
      <h3 class="text-[0.67rem] tracking-[0.08em] uppercase font-extrabold text-[#4f4b59]">
        Schedule
      </h3>
      <span class="text-[#5f5a67] text-[0.72rem] leading-[1.3]">{{ timezoneLabel }}</span>
    </div>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-1.5">
      <div
        class="border-2 border-[#d0c9d8] rounded-[14px] bg-white px-2.5 py-2 outline-none cursor-pointer transition-[border-color,background-color,box-shadow] duration-[160ms] ease-in-out hover:border-[#1565c0] focus-visible:border-[#1565c0]"
        :class="{
          'schedule-card-active border-[#1565c0] bg-[#edf3ff] shadow-[inset_0_0_0_1px_rgba(21,101,192,0.05)]':
            scheduleMode === 'interval',
        }"
        tabindex="0"
        role="button"
        @click="scheduleMode = 'interval'"
        @keydown.enter.prevent="scheduleMode = 'interval'"
        @keydown.space.prevent="scheduleMode = 'interval'"
      >
        <div class="flex items-start gap-[5px]">
          <span
            class="size-4 rounded-full border-2 shrink-0 mt-px"
            :class="
              scheduleMode === 'interval'
                ? 'border-[#1565c0] shadow-[inset_0_0_0_3px_#1565c0] bg-white'
                : 'border-[#7e7886]'
            "
          />
          <div class="text-[0.79rem] font-bold text-[#1f1d24] leading-[1.2]">
            Repeating interval
          </div>
        </div>

        <div
          v-if="scheduleMode === 'interval'"
          class="flex items-center gap-[5px] mt-1 pl-7 flex-wrap max-[900px]:pl-0"
        >
          <span class="text-[0.74rem] font-medium text-[#1f1d24]">Every</span>
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
            class="max-w-[110px]"
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
        class="border-2 border-[#d0c9d8] rounded-[14px] bg-white px-2.5 py-2 outline-none cursor-pointer transition-[border-color,background-color,box-shadow] duration-[160ms] ease-in-out hover:border-[#1565c0] focus-visible:border-[#1565c0]"
        :class="{
          'schedule-card-active border-[#1565c0] bg-[#edf3ff] shadow-[inset_0_0_0_1px_rgba(21,101,192,0.05)]':
            scheduleMode === 'crontab',
        }"
        tabindex="0"
        role="button"
        @click="scheduleMode = 'crontab'"
        @keydown.enter.prevent="scheduleMode = 'crontab'"
        @keydown.space.prevent="scheduleMode = 'crontab'"
      >
        <div class="flex items-start gap-[5px]">
          <span
            class="size-4 rounded-full border-2 shrink-0 mt-px"
            :class="
              scheduleMode === 'crontab'
                ? 'border-[#1565c0] shadow-[inset_0_0_0_3px_#1565c0] bg-white'
                : 'border-[#7e7886]'
            "
          />
          <div>
            <div class="text-[0.79rem] font-bold text-[#1f1d24] leading-[1.2]">
              Crontab expression
            </div>
            <div class="mt-px text-[#5f5a67] text-[0.68rem] leading-[1.25]">
              Advanced cron syntax
            </div>
          </div>
        </div>

        <div
          v-if="scheduleMode === 'crontab'"
          class="flex items-center gap-[5px] mt-1 pl-7 flex-wrap max-[900px]:pl-0"
        >
          <v-text-field
            v-model="task.schedule!.crontab"
            class="w-full max-[640px]:max-w-full"
            placeholder="0 9 * * *"
            hide-details
            variant="outlined"
            rounded="lg"
            density="compact"
          />
        </div>
      </div>
    </div>

    <div class="flex items-center gap-1.5 flex-wrap">
      <label class="text-[0.74rem] font-medium text-[#1f1d24]" for="task-start-time">
        Start
      </label>
      <v-text-field
        id="task-start-time"
        v-model="startInput"
        class="schedule-start-input max-w-[220px] max-[640px]:max-w-full max-[640px]:w-full"
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
.schedule-card-active :deep(.v-field) {
  background: #ffffff;
}
.schedule-card-active :deep(.v-field__overlay) {
  background: transparent;
}
.schedule-card-active :deep(.v-field__outline) {
  --v-field-border-opacity: 1;
}
</style>
