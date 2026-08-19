<template>
  <div class="qc-session-list">
    <div class="qc-session-list__header px-1 py-1 d-flex align-center ga-2">
      <v-icon icon="mdi-source-branch" color="primary" size="16" />
      <span class="text-body-small font-weight-medium">Sessions</span>
      <v-spacer />
      <v-btn
        v-if="isReadOnly && currentSessionId"
        data-testid="session-return-current"
        size="x-small"
        variant="tonal"
        color="primary"
        @click="returnToCurrent"
      >
        Return to current
      </v-btn>
    </div>

    <div
      v-if="!sessions.length"
      class="pa-3 text-center text-body-small text-medium-emphasis"
    >
      No sessions yet.
    </div>

    <v-timeline
      v-else
      side="end"
      align="start"
      density="compact"
      truncate-line="both"
      line-thickness="2"
      class="qc-session-list__timeline px-2 py-2"
    >
      <v-timeline-item
        v-for="session of orderedSessions"
        :key="session.id"
        fill-dot
        size="x-small"
        :icon="session.status === 'in_progress' ? 'mdi-pencil' : 'mdi-check'"
        :icon-color="session.status === 'in_progress' ? 'warning' : 'success'"
        width="100%"
        :data-testid="`session-${session.id}`"
        class="qc-session-list__item qc-timeline__item"
        :class="[
          session.status === 'in_progress'
            ? 'qc-timeline__item--active'
            : 'qc-timeline__item--done',
          { 'qc-timeline__item--viewed': session.id === viewedSessionId },
        ]"
      >
        <!-- Only the header selects; clicks inside the nested panel must not. -->
        <div
          class="d-flex align-center ga-2 cursor-pointer"
          :data-testid="`session-header-${session.id}`"
          @click="onSelect(session)"
        >
          <div class="flex-grow-1" style="min-width: 0">
            <div class="text-body-small font-weight-medium text-truncate">
              {{ sessionLabel(session) }}
            </div>
            <div
              v-if="session.description"
              class="text-body-small text-medium-emphasis text-truncate"
            >
              {{ sessionPeriod(session) }}
            </div>
          </div>
          <v-chip
            v-if="session.id === currentSessionId"
            size="x-small"
            color="warning"
            variant="tonal"
            label
          >
            Editing
          </v-chip>
          <v-chip v-else size="x-small" color="grey" variant="tonal" label>
            View
          </v-chip>
        </div>

        <div v-if="session.id === viewedSessionId" class="mt-2">
          <slot name="operations" />
        </div>
        <div
          v-else-if="operationCount(session)"
          class="text-body-small text-medium-emphasis mt-1 cursor-pointer"
          :data-testid="`session-preview-${session.id}`"
          @click="onSelect(session)"
        >
          {{ previewLabel(session) }}
        </div>
        <div
          v-else
          class="text-body-small text-medium-emphasis font-italic mt-1"
          :data-testid="`session-preview-${session.id}`"
        >
          No operations.
        </div>
      </v-timeline-item>
    </v-timeline>

    <div v-if="!viewedSessionId" class="pa-2">
      <slot name="operations" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useQcSessionStore } from '@/store/qcSession'
import { formatDateRange } from '@/utils/time'
import type { QualityControlSession } from '@hydroserver/client'

const store = useQcSessionStore()
const { sessions, currentSessionId, viewedSessionId, isReadOnly } =
  storeToRefs(store)

// Oldest first by creation time. Phenomenon start orders by the edited
// window, which says nothing about recency and ties on equal windows.
const orderedSessions = computed(() =>
  [...sessions.value].sort((a, b) => a.createdAt.localeCompare(b.createdAt))
)

const sessionPeriod = (session: QualityControlSession): string =>
  formatDateRange(session.phenomenonTimeStart, session.phenomenonTimeEnd)

const operationCount = (session: QualityControlSession): number =>
  (session as { operations?: unknown[] }).operations?.length ?? 0

function previewLabel(session: QualityControlSession): string {
  const total = operationCount(session)
  return `${total} operation${total === 1 ? '' : 's'}`
}

function sessionLabel(session: QualityControlSession): string {
  return session.description || sessionPeriod(session)
}

const emit = defineEmits<{ (e: 'view', sessionId: string): void }>()

function onSelect(session: QualityControlSession): void {
  emit('view', session.id)
}

function returnToCurrent(): void {
  if (currentSessionId.value) emit('view', currentSessionId.value)
}
</script>

<style scoped>
.qc-session-list__header {
  min-height: 28px;
}

</style>
