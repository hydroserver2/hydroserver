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
              v-for="s in orderedSessions(opt.sessions)"
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
                </div>

                <v-chip
                  size="x-small"
                  :color="s.status === 'in_progress' ? 'warning' : 'grey'"
                  variant="tonal"
                  label
                  class="flex-shrink-0"
                >
                  {{ s.status === 'in_progress' ? 'In progress' : 'Committed' }}
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
                <v-btn
                  icon="mdi-trash-can-outline"
                  size="x-small"
                  variant="text"
                  color="error"
                  class="flex-shrink-0"
                  :data-testid="`delete-session-${s.id}`"
                  :title="deleteHint(opt, s)"
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

  <v-dialog v-model="confirmOpen" max-width="560" persistent>
    <v-card rounded="lg" data-testid="delete-session-dialog">
      <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
        <v-avatar color="error" variant="tonal" size="40">
          <v-icon icon="mdi-delete-alert-outline" size="22" />
        </v-avatar>
        <div class="d-flex flex-column">
          <div class="text-title-large font-weight-bold">
            {{
              chainCount > 1
                ? `Delete ${chainCount} sessions?`
                : 'Delete this session?'
            }}
          </div>
          <div class="text-body-small text-medium-emphasis">
            This permanently removes quality control work
          </div>
        </div>
      </div>

      <v-card-text class="pt-2 pb-4 px-6">
        <p class="text-body-medium mb-3">
          <template v-if="chainCount > 1">
            Later sessions were built on this one, so they go too. Deleting
            only the one you picked would leave them describing edits that no
            longer exist.
          </template>
          <template v-else>
            Its operations and the record of them are removed.
          </template>
        </p>

        <div class="text-body-small font-weight-medium mb-1">
          {{ chainCount > 1 ? 'Will be deleted, newest first' : 'Will be deleted' }}
        </div>
        <v-list
          density="compact"
          class="py-0 mb-3 rounded border"
          :lines="false"
          data-testid="delete-session-chain"
        >
          <v-list-item
            v-for="s in chainSessions"
            :key="s.id"
            :data-testid="`delete-chain-item-${s.id}`"
          >
            <template #prepend>
              <v-icon
                :icon="
                  s.id === confirmingSessionId
                    ? 'mdi-target'
                    : 'mdi-subdirectory-arrow-right'
                "
                :color="s.id === confirmingSessionId ? 'error' : 'warning'"
                size="16"
                class="mr-2"
              />
            </template>
            <v-list-item-title class="text-body-small">
              {{ sessionLabel(s) }}
              <span v-if="s.id === confirmingSessionId" class="text-medium-emphasis">
                (the one you picked)
              </span>
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

        <div
          class="text-body-small text-medium-emphasis mb-3"
          data-testid="delete-session-dependents-note"
        >
          Any session built on this one is deleted with it.
        </div>

        <v-alert type="error" variant="tonal" density="compact">
          <span class="text-body-small">This cannot be undone.</span>
        </v-alert>

        <!-- Extra affirmation only when the cascade reaches beyond the
             session the user actually pointed at. -->
        <v-checkbox
          v-if="chainCount > 1"
          v-model="cascadeAcknowledged"
          density="compact"
          hide-details
          color="error"
          class="mt-2"
          data-testid="delete-session-acknowledge"
        >
          <template #label>
            <span class="text-body-small">
              I understand {{ chainCount }} sessions will be deleted
            </span>
          </template>
        </v-checkbox>
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
          :disabled="confirmDisabled"
          :data-testid="`confirm-delete-session-${confirmingSessionId}`"
          @click="onDeleteSession"
        >
          {{ chainCount > 1 ? `Delete ${chainCount} sessions` : 'Delete session' }}
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
import { collectDeletionChain } from '@/utils/sessionGraph'

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
// id of the session whose delete is awaiting confirmation, and the option
// it belongs to, so the chain can be resolved against that option's sessions.
const confirmingSessionId = ref<string | null>(null)
const confirmingOption = ref<ManagedDatastreamOption | null>(null)
const cascadeAcknowledged = ref(false)

const confirmOpen = computed({
  get: () => !!confirmingSessionId.value,
  set: (open: boolean) => {
    if (!open) closeConfirm()
  },
})

/** The sessions this delete would remove, in the order they go. */
const chainSessions = computed<QualityControlSession[]>(() => {
  const opt = confirmingOption.value
  const targetId = confirmingSessionId.value
  if (!opt || !targetId) return []
  const byId = new Map(opt.sessions.map((s) => [s.id, s]))
  return collectDeletionChain(opt.sessions, targetId)
    .map((id) => byId.get(id))
    .filter((s): s is QualityControlSession => !!s)
})

const chainCount = computed(() => chainSessions.value.length)

// A cascade needs the checkbox; a single session just needs the button.
const confirmDisabled = computed(
  () => chainCount.value > 1 && !cascadeAcknowledged.value
)

const deleteHint = (opt: ManagedDatastreamOption, s: QualityControlSession) => {
  const count = collectDeletionChain(opt.sessions, s.id).length
  return count > 1
    ? `Delete this session and the ${count - 1} built on it`
    : 'Delete this session'
}

function openConfirm(opt: ManagedDatastreamOption, s: QualityControlSession) {
  confirmingOption.value = opt
  confirmingSessionId.value = s.id
  cascadeAcknowledged.value = false
}

function closeConfirm() {
  confirmingSessionId.value = null
  confirmingOption.value = null
  cascadeAcknowledged.value = false
}

function onDelete(opt: ManagedDatastreamOption) {
  confirmingDeleteId.value = null
  emit('delete', opt)
}

function onDeleteSession() {
  const opt = confirmingOption.value
  const sessionId = confirmingSessionId.value
  closeConfirm()
  if (opt && sessionId) emit('deleteSession', opt, sessionId)
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

const orderedSessions = (sessions: QualityControlSession[]) =>
  [...sessions].sort((a, b) => a.createdAt.localeCompare(b.createdAt))

const sessionPeriod = (s: QualityControlSession) =>
  formatDateRange(s.phenomenonTimeStart, s.phenomenonTimeEnd)

const sessionLabel = (s: QualityControlSession) =>
  s.description || sessionPeriod(s)
</script>
