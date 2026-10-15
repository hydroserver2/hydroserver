<template>
  <div class="edit-history-step-details px-3 py-2">
    <div class="text-body-small text-medium-emphasis mb-1">Arguments</div>
    <ul class="edit-history-step-details__args pa-0 ma-0 overflow-y-auto">
      <li
        v-for="(arg, argIdx) of entry.args"
        :key="argIdx"
        class="text-body-small px-1 py-1"
        style="word-break: break-all"
      >
        <code class="text-body-small">{{ formatArg(arg) }}</code>
      </li>
    </ul>

    <!-- Dev-only: whether the dispatch ran on a worker or inline. -->
    <div
      v-if="applied && isDev && entry.execution?.mode"
      class="text-body-small text-medium-emphasis mt-3 d-flex align-center ga-2"
      :data-testid="`history-execution-${index}`"
    >
      <v-chip
        size="x-small"
        variant="tonal"
        :color="entry.execution.mode === 'inline' ? 'success' : 'primary'"
        class="edit-history-step-details__mode"
        :title="
          entry.execution.mode === 'inline'
            ? 'Ran on the main thread (inline)'
            : 'Ran on a web worker'
        "
      >
        {{ entry.execution.mode }}
      </v-chip>
    </div>

    <div
      v-if="entry.performedBy"
      class="text-body-small text-medium-emphasis mt-3"
      :data-testid="`history-author-detail-${index}`"
    >
      Applied by {{ entry.performedBy }}
    </div>

    <div class="text-body-small text-medium-emphasis mt-3 mb-1">Comment</div>
    <v-textarea
      v-if="!readOnly"
      :model-value="entry.comment ?? ''"
      :data-testid="`history-comment-${index}`"
      placeholder="Why was this operation applied?"
      variant="outlined"
      density="compact"
      rows="2"
      auto-grow
      hide-details
      class="text-body-small"
      @update:model-value="emit('update:comment', $event)"
    />
    <div
      v-else
      class="text-body-small"
      :class="{ 'text-medium-emphasis font-italic': !entry.comment }"
      :data-testid="`history-comment-readonly-${index}`"
    >
      {{ entry.comment || 'No comment.' }}
    </div>
  </div>
</template>

<script setup lang="ts">
/** The expanded part of an edit history step: its arguments, who applied
 *  it, and its comment. */

import type { HistoryItem } from '@uwrl/qc-utils'

defineProps<{
  entry: HistoryItem
  index: number
  /** False for a step past the one on screen, whose run no longer holds. */
  applied: boolean
  readOnly: boolean
}>()

const emit = defineEmits<{ (e: 'update:comment', value: string): void }>()

const isDev = import.meta.env.DEV

function formatArg(arg: unknown): string {
  if (Array.isArray(arg)) {
    const len = arg.length
    if (!len) return '[]'
    const preview = arg
      .slice(0, 5)
      .map((v) => (typeof v === 'number' ? v : JSON.stringify(v)))
      .join(', ')
    return len <= 5 ? `[${preview}]` : `[${preview}, … (${len} items)]`
  }
  if (arg && typeof arg === 'object') {
    try {
      return JSON.stringify(arg)
    } catch {
      return String(arg)
    }
  }
  return String(arg)
}
</script>

<style scoped>
.edit-history-step-details {
  background-color: rgba(var(--v-theme-primary), 0.03);
  border-left: 2px solid rgb(var(--v-theme-primary));
}

.edit-history-step-details__args {
  list-style: none;
  max-height: 12rem;
}

.edit-history-step-details__mode {
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  height: 16px;
  padding-inline: 6px;
}
</style>
