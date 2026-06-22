<template>
  <div class="qc-session-list">
    <div class="qc-session-list__header px-3 py-2 d-flex align-center ga-2">
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

    <v-divider />

    <div
      v-if="!sessions.length"
      class="pa-3 text-center text-body-small text-medium-emphasis"
    >
      No sessions yet.
    </div>

    <v-list v-else density="compact" class="py-0" :lines="false">
      <v-list-item
        v-for="session of orderedSessions"
        :key="session.id"
        :active="session.id === viewedSessionId"
        :data-testid="`session-${session.id}`"
        @click="onSelect(session)"
      >
        <template #prepend>
          <v-icon
            :icon="
              session.status === 'in_progress'
                ? 'mdi-pencil-circle'
                : 'mdi-check-circle'
            "
            :color="session.status === 'in_progress' ? 'warning' : 'success'"
            size="16"
            class="mr-2"
          />
        </template>

        <v-list-item-title class="text-body-small">
          {{ sessionLabel(session) }}
        </v-list-item-title>

        <template #append>
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
        </template>
      </v-list-item>
    </v-list>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useQcSessionStore } from '@/store/qcSession'
import type { QualityControlSession } from '@hydroserver/client'

const store = useQcSessionStore()
const { sessions, currentSessionId, viewedSessionId, isReadOnly } =
  storeToRefs(store)

// Newest first, by phenomenon start (ISO sorts chronologically).
const orderedSessions = computed(() =>
  [...sessions.value].sort((a, b) =>
    b.phenomenonTimeStart.localeCompare(a.phenomenonTimeStart)
  )
)

function sessionLabel(session: QualityControlSession): string {
  if (session.description) return session.description
  return `${session.phenomenonTimeStart.slice(0, 10)} to ${session.phenomenonTimeEnd.slice(0, 10)}`
}

function onSelect(session: QualityControlSession): void {
  if (session.id === store.currentSessionId) {
    store.returnToCurrent()
  } else {
    store.viewSession(session.id)
  }
}

function returnToCurrent(): void {
  store.returnToCurrent()
}
</script>

<style scoped>
.qc-session-list__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 32px;
}
</style>
