<template>
  <v-card rounded="lg">
    <div class="px-4 pt-4 pb-2">
      <div class="text-title-medium font-weight-bold">
        Quality-control "{{ source.name }}"
      </div>
      <div class="text-body-small text-medium-emphasis mt-1">
        Continue an in-progress session, start a new one over the current time
        range, or set up a new managed datastream.
      </div>
    </div>

    <v-divider />

    <div class="qc-chooser__body pa-4">
      <div v-if="loading" class="py-6 text-center">
        <v-progress-circular indeterminate color="primary" size="28" />
      </div>

      <template v-else>
        <div
          v-if="!options.length"
          class="text-body-small text-medium-emphasis mb-3"
        >
          No QC datastreams for this source yet. Create one to start editing.
        </div>

        <v-card
          v-for="opt in options"
          :key="opt.historyId"
          variant="outlined"
          class="mb-3"
        >
          <div class="px-3 py-2 d-flex align-center ga-2">
            <v-icon icon="mdi-pencil-box-outline" color="primary" size="18" />
            <div class="d-flex flex-column" style="min-width: 0">
              <span class="text-body-medium font-weight-medium">
                {{ opt.managed.name }}
              </span>
              <span class="text-body-small text-medium-emphasis">
                {{ summary(opt) }}
              </span>
            </div>
            <v-spacer />
            <v-btn
              size="small"
              color="primary"
              variant="flat"
              :data-testid="`edit-managed-${opt.managed.id}`"
              @click="emit('edit', opt)"
            >
              {{ hasInProgress(opt) ? 'Continue session' : 'Start new session' }}
            </v-btn>
            <v-btn
              icon="mdi-trash-can-outline"
              size="small"
              variant="text"
              color="error"
              :data-testid="`delete-managed-${opt.managed.id}`"
              title="Delete this managed datastream"
              @click="confirmingDeleteId = opt.historyId"
            />
          </div>

          <v-alert
            v-if="confirmingDeleteId === opt.historyId"
            type="warning"
            variant="tonal"
            density="compact"
            class="mx-3 mb-2"
          >
            <div class="d-flex align-center flex-wrap ga-2">
              <span class="text-body-small">
                Delete "{{ opt.managed.name }}" and its
                {{ opt.sessions.length }} session{{
                  opt.sessions.length === 1 ? '' : 's'
                }}? This can't be undone.
              </span>
              <v-spacer />
              <v-btn
                size="x-small"
                variant="text"
                @click="confirmingDeleteId = null"
              >
                Cancel
              </v-btn>
              <v-btn
                size="x-small"
                color="error"
                variant="flat"
                :data-testid="`confirm-delete-${opt.managed.id}`"
                @click="onDelete(opt)"
              >
                Delete
              </v-btn>
            </div>
          </v-alert>

          <v-divider />

          <div
            v-if="!opt.sessions.length"
            class="px-3 py-2 text-body-small text-medium-emphasis"
          >
            No sessions yet.
          </div>
          <v-list v-else density="compact" class="py-0" :lines="false">
            <v-list-item
              v-for="s in orderedSessions(opt.sessions)"
              :key="s.id"
              :data-testid="`chooser-session-${s.id}`"
            >
              <template #prepend>
                <v-icon
                  :icon="
                    s.status === 'in_progress'
                      ? 'mdi-pencil-circle'
                      : 'mdi-check-circle'
                  "
                  :color="s.status === 'in_progress' ? 'warning' : 'success'"
                  size="16"
                  class="mr-2"
                />
              </template>
              <v-list-item-title class="text-body-small">
                {{ sessionLabel(s) }}
              </v-list-item-title>
              <template #append>
                <v-chip
                  size="x-small"
                  :color="s.status === 'in_progress' ? 'warning' : 'grey'"
                  variant="tonal"
                  label
                >
                  {{ s.status === 'in_progress' ? 'In progress' : 'Committed' }}
                </v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-card>

        <v-btn
          block
          variant="tonal"
          color="primary"
          prepend-icon="mdi-plus"
          data-testid="chooser-create-managed"
          @click="emit('create')"
        >
          Create new managed datastream
        </v-btn>
      </template>
    </div>

    <v-divider />

    <v-card-actions class="px-4 py-2">
      <v-spacer />
      <v-btn variant="text" data-testid="chooser-cancel" @click="emit('cancel')">
        Cancel
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Datastream, QualityControlSession } from '@hydroserver/client'
import type { ManagedDatastreamOption } from '@/composables/useManagedDatastreams'
import { formatDateRange } from '@/utils/time'

defineProps<{
  source: Datastream
  options: ManagedDatastreamOption[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', option: ManagedDatastreamOption): void
  (e: 'delete', option: ManagedDatastreamOption): void
  (e: 'create'): void
  (e: 'cancel'): void
}>()

// historyId of the managed datastream whose delete is awaiting confirmation.
const confirmingDeleteId = ref<string | null>(null)

function onDelete(opt: ManagedDatastreamOption) {
  confirmingDeleteId.value = null
  emit('delete', opt)
}

const NUMBER = new Intl.NumberFormat()

// One-line recap so multiple managed datastreams are distinguishable:
// processing level, observation count, and session summary.
function summary(opt: ManagedDatastreamOption): string {
  const parts: string[] = []
  const level =
    opt.managed.processingLevel?.definition ||
    opt.managed.processingLevel?.code ||
    null
  if (level) parts.push(`Level: ${level}`)
  parts.push(`${NUMBER.format(opt.managed.valueCount ?? 0)} obs`)
  const inProgress = opt.sessions.filter(
    (s) => s.status === 'in_progress'
  ).length
  const sessionText = `${opt.sessions.length} session${
    opt.sessions.length === 1 ? '' : 's'
  }${inProgress ? `, ${inProgress} in progress` : ''}`
  parts.push(sessionText)
  return parts.join(' · ')
}

const hasInProgress = (opt: ManagedDatastreamOption) =>
  opt.sessions.some((s) => s.status === 'in_progress')

// Newest first by phenomenon start (ISO sorts chronologically).
const orderedSessions = (sessions: QualityControlSession[]) =>
  [...sessions].sort((a, b) =>
    b.phenomenonTimeStart.localeCompare(a.phenomenonTimeStart)
  )

const sessionLabel = (s: QualityControlSession) =>
  s.description ||
  formatDateRange(s.phenomenonTimeStart, s.phenomenonTimeEnd)
</script>
