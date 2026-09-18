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

          <v-timeline
            side="end"
            align="start"
            density="compact"
            truncate-line="both"
            line-thickness="2"
            class="px-3 py-2"
          >
            <!-- Heads the timeline as its own node so starting a session
                 reads as part of the history rather than a header action. -->
            <v-timeline-item
              v-if="!hasInProgress(opt)"
              fill-dot
              size="x-small"
              width="100%"
              icon="mdi-plus"
              icon-color="primary"
              class="qc-timeline__item qc-timeline__item--new"
            >
              <div class="d-flex align-center ga-2">
                <div class="flex-grow-1 text-body-small text-medium-emphasis">
                  {{
                    opt.sessions.length
                      ? 'Continue from the latest commit'
                      : 'No sessions yet'
                  }}
                </div>
                <v-btn
                  size="small"
                  color="primary"
                  variant="flat"
                  class="flex-shrink-0"
                  :data-testid="`edit-managed-${opt.managed.id}`"
                  @click="emit('edit', opt)"
                >
                  Start new session
                </v-btn>
              </div>
            </v-timeline-item>

            <v-timeline-item
              v-for="(s, i) in orderedSessions(opt.sessions)"
              :key="s.id"
              fill-dot
              size="x-small"
              width="100%"
              :icon="s.status === 'in_progress' ? 'mdi-pencil' : 'mdi-check'"
              :icon-color="s.status === 'in_progress' ? 'warning' : 'success'"
              :data-testid="`chooser-session-${s.id}`"
              class="qc-timeline__item"
              :class="
                s.status === 'in_progress'
                  ? 'qc-timeline__item--active'
                  : 'qc-timeline__item--done'
              "
            >
              <div class="d-flex align-center ga-2">
                <div class="flex-grow-1" style="min-width: 0">
                  <div class="text-body-small font-weight-medium text-truncate">
                    {{ sessionLabel(s) }}
                  </div>
                  <div
                    v-if="s.description"
                    class="text-body-small text-medium-emphasis text-truncate"
                  >
                    {{ sessionPeriod(s) }}
                  </div>
                  <!-- The Continue button carries this state visually, so the
                       row only needs it spelled out for screen readers. -->
                  <span v-if="s.status === 'in_progress'" class="d-sr-only">
                    In progress
                  </span>
                </div>

                <v-chip
                  v-if="s.status !== 'in_progress'"
                  size="x-small"
                  color="grey"
                  variant="tonal"
                  label
                  class="flex-shrink-0"
                >
                  Committed
                </v-chip>

                <v-btn
                  v-if="s.status === 'in_progress'"
                  size="small"
                  color="primary"
                  variant="flat"
                  class="flex-shrink-0"
                  :data-testid="`continue-session-${s.id}`"
                  @click="emit('edit', opt)"
                >
                  Continue
                </v-btn>
                <!-- Only the newest session can be deleted: anything older may
                     have sessions built on it. -->
                <v-btn
                  v-if="i === opt.sessions.length - 1"
                  icon="mdi-trash-can-outline"
                  size="x-small"
                  variant="text"
                  color="error"
                  class="flex-shrink-0"
                  :data-testid="`delete-session-${s.id}`"
                  title="Delete this session"
                  @click="openConfirm(opt, s)"
                />
              </div>
            </v-timeline-item>
          </v-timeline>
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

  <v-dialog v-model="confirmOpen" max-width="480" persistent>
    <v-card rounded="lg" data-testid="delete-session-dialog">
      <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
        <v-avatar color="error" variant="tonal" size="40">
          <v-icon icon="mdi-delete-alert-outline" size="22" />
        </v-avatar>
        <div class="d-flex flex-column">
          <div class="text-title-large font-weight-bold">
            Delete this session?
          </div>
          <div class="text-body-small text-medium-emphasis">
            This permanently removes quality control work
          </div>
        </div>
      </div>

      <v-card-text v-if="confirmingSession" class="pt-2 pb-4 px-6">
        <p class="text-body-medium mb-3">
          "{{ sessionLabel(confirmingSession) }}" and the record of its
          operations are removed. Earlier sessions are untouched.
        </p>

        <v-alert type="error" variant="tonal" density="compact">
          <span class="text-body-small">This cannot be undone.</span>
        </v-alert>
      </v-card-text>

      <v-divider />
      <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
        <v-btn variant="text" data-testid="cancel-delete-session" @click="closeConfirm">
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          color="error"
          variant="flat"
          prepend-icon="mdi-delete-outline"
          :data-testid="`confirm-delete-session-${confirmingSession?.id}`"
          @click="onDeleteSession"
        >
          Delete session
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Datastream, QualityControlSession } from '@hydroserver/client'
import type { ManagedDatastreamOption } from '@/composables/useManagedDatastreams'
import { formatDateRange } from '@/utils/time'
import { datastreamSummary } from '@/utils/datastreamSummary'

defineProps<{
  source: Datastream
  options: ManagedDatastreamOption[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', option: ManagedDatastreamOption): void
  (e: 'delete', option: ManagedDatastreamOption): void
  (e: 'deleteSession', option: ManagedDatastreamOption, sessionId: string): void
  (e: 'create'): void
  (e: 'cancel'): void
}>()

// historyId of the managed datastream whose delete is awaiting confirmation.
const confirmingDeleteId = ref<string | null>(null)
// The session whose delete is awaiting confirmation, and the option it
// belongs to, so the emit can name both.
const confirmingSession = ref<QualityControlSession | null>(null)
const confirmingOption = ref<ManagedDatastreamOption | null>(null)

const confirmOpen = computed({
  get: () => !!confirmingSession.value,
  set: (open: boolean) => {
    if (!open) closeConfirm()
  },
})

function openConfirm(opt: ManagedDatastreamOption, s: QualityControlSession) {
  confirmingOption.value = opt
  confirmingSession.value = s
}

function closeConfirm() {
  confirmingSession.value = null
  confirmingOption.value = null
}

function onDelete(opt: ManagedDatastreamOption) {
  confirmingDeleteId.value = null
  emit('delete', opt)
}

function onDeleteSession() {
  const opt = confirmingOption.value
  const sessionId = confirmingSession.value?.id
  closeConfirm()
  if (opt && sessionId) emit('deleteSession', opt, sessionId)
}

const summary = (opt: ManagedDatastreamOption) =>
  datastreamSummary(opt.managed, opt.sessions)

const hasInProgress = (opt: ManagedDatastreamOption) =>
  opt.sessions.some((s) => s.status === 'in_progress')

const orderedSessions = (sessions: QualityControlSession[]) =>
  [...sessions].sort((a, b) => a.createdAt.localeCompare(b.createdAt))

const sessionPeriod = (s: QualityControlSession) =>
  formatDateRange(s.phenomenonTimeStart, s.phenomenonTimeEnd)

const sessionLabel = (s: QualityControlSession) =>
  s.description || sessionPeriod(s)
</script>
