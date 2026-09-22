<template>
  <v-card rounded="lg">
    <div class="px-4 pt-4 pb-2">
      <div class="text-title-medium font-weight-bold">
        New session on "{{ managedName }}"
      </div>
      <div class="text-body-small text-medium-emphasis mt-1">
        The window starts out covering the whole source record. Narrow it to
        the period you want to edit: it can overlap committed sessions but
        cannot leave a gap before or after them.
      </div>
    </div>

    <v-divider />

    <div class="pa-4 d-flex flex-column ga-3">
      <div class="text-body-small">
        <div>
          <span class="text-medium-emphasis">Source data:</span>
          {{ formatDateRange(source.phenomenonBeginTime, source.phenomenonEndTime) }}
        </div>
        <div data-testid="session-window-committed">
          <span class="text-medium-emphasis">Committed history:</span>
          <template v-if="history">
            {{ formatDateRange(history.begin.toISOString(), history.end.toISOString()) }}
          </template>
          <template v-else>Nothing committed yet</template>
        </div>
      </div>

      <template v-if="begin && end">
        <div v-if="presets.length" class="session-window__presets">
          <span
            v-for="preset in presets"
            :key="preset.id"
            :data-testid="`session-window-preset-slot-${preset.id}`"
            :title="preset.disabledReason ?? preset.title"
          >
            <v-chip
              :data-testid="`session-window-preset-${preset.id}`"
              :color="activePresetId === preset.id ? 'primary' : undefined"
              :variant="activePresetId === preset.id ? 'tonal' : 'outlined'"
              size="small"
              role="button"
              :aria-pressed="String(activePresetId === preset.id)"
              :disabled="!!preset.disabledReason"
              class="session-window__preset-chip"
              @click="applyPreset(preset)"
            >
              {{ preset.label }}
            </v-chip>
          </span>
        </div>

        <div>
          <div class="text-body-small text-medium-emphasis mb-1">From</div>
          <DatePickerField
            v-model="begin"
            data-testid="session-window-from"
            placeholder="Start date"
          />
        </div>
        <div>
          <div class="text-body-small text-medium-emphasis mb-1">To</div>
          <DatePickerField
            v-model="end"
            data-testid="session-window-to"
            placeholder="End date"
          />
        </div>
      </template>

      <v-alert
        v-if="issue"
        type="warning"
        variant="tonal"
        density="compact"
        data-testid="session-window-error"
      >
        <span class="text-body-small">{{ issue.message }}</span>
        <div v-if="issue.fix" class="mt-2">
          <v-btn
            size="small"
            variant="tonal"
            data-testid="session-window-fix"
            @click="applyFix(issue.fix)"
          >
            {{ issue.fix.label }}
          </v-btn>
        </div>
      </v-alert>
    </div>

    <v-divider />

    <v-card-actions class="px-4 py-2">
      <v-spacer />
      <v-btn
        variant="text"
        data-testid="session-window-cancel"
        :disabled="loading"
        @click="emit('cancel')"
      >
        Cancel
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        data-testid="session-window-start"
        :disabled="!!issue"
        :loading="loading"
        @click="onStart"
      >
        Start session
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'
import { formatDateRange } from '@/utils/time'
import type { TimeWindow } from '@/utils/timeRangePresets'
import {
  NO_SOURCE_DATA_ISSUE,
  committedExtent,
  defaultSessionWindow,
  sessionWindowIssue,
  sessionWindowPresets,
  type SessionRange,
  type SessionWindowFix,
  type SessionWindowIssue,
  type SessionWindowPreset,
  type SourceExtent,
} from '@/utils/sessionWindow'

const props = defineProps<{
  managedName: string
  source: SourceExtent
  sessions: readonly SessionRange[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'confirm', window: TimeWindow): void
  (e: 'cancel'): void
}>()

const initial = defaultSessionWindow(props.source)
const begin = ref<Date | null>(initial?.begin ?? null)
const end = ref<Date | null>(initial?.end ?? null)

const history = computed(() => committedExtent(props.sessions))
const presets = computed(() => sessionWindowPresets(props.source, props.sessions))

const issue = computed<SessionWindowIssue | null>(() => {
  if (!begin.value || !end.value) return NO_SOURCE_DATA_ISSUE
  return sessionWindowIssue(
    { begin: begin.value, end: end.value },
    props.source,
    props.sessions
  )
})

const activePresetId = computed(() => {
  const from = begin.value?.getTime()
  const to = end.value?.getTime()
  if (from === undefined || to === undefined) return null
  return (
    presets.value.find(
      (p) => p.window.begin.getTime() === from && p.window.end.getTime() === to
    )?.id ?? null
  )
})

function applyPreset(preset: SessionWindowPreset) {
  begin.value = new Date(preset.window.begin)
  end.value = new Date(preset.window.end)
}

// Only the endpoints the fix names move; a valid one is left as the user set it.
function applyFix(fix: SessionWindowFix) {
  if (fix.begin) begin.value = new Date(fix.begin)
  if (fix.end) end.value = new Date(fix.end)
}

function onStart() {
  if (issue.value || !begin.value || !end.value) return
  emit('confirm', { begin: begin.value, end: end.value })
}
</script>

<style scoped>
.session-window__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.session-window__preset-chip {
  font-size: 0.75rem !important;
  height: 26px !important;
}
</style>
