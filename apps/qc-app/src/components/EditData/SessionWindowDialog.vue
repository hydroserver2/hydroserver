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
        v-if="error"
        type="warning"
        variant="tonal"
        density="compact"
        data-testid="session-window-error"
      >
        <span class="text-body-small">{{ error }}</span>
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
        :disabled="!!error"
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
  committedExtent,
  defaultSessionWindow,
  validateSessionWindow,
  type SessionRange,
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

const error = computed(() => {
  if (!begin.value || !end.value) {
    return 'The source datastream has no observations to edit.'
  }
  return validateSessionWindow(
    { begin: begin.value, end: end.value },
    props.source,
    props.sessions
  )
})

function onStart() {
  if (error.value || !begin.value || !end.value) return
  emit('confirm', { begin: begin.value, end: end.value })
}
</script>
