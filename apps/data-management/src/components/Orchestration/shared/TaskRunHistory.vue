<template>
  <template v-if="showLoading">
    <div class="run-loading">
      <v-progress-circular
        indeterminate
        size="20"
        width="2"
        color="blue-grey-darken-1"
      />
      <span>Loading run history...</span>
    </div>
  </template>

  <template v-else-if="rows.length">
    <template v-for="run in rows" :key="run.id">
      <div
        :id="run.domId"
        class="run-entry"
        :class="{ 'run-highlight': highlightedRunId === run.id }"
      >
        <div class="run-entry-top">
          <div class="run-entry-top-left">
            <TaskStatus
              :status="getRunStatusText(run.raw)"
              :paused="false"
              class="run-entry-status"
            />
          </div>
          <div class="run-entry-summary" :title="run.message">
            {{ run.message }}
          </div>
          <div class="run-entry-runid-right">Run {{ shortId(run.id) }}</div>
        </div>

        <div class="run-entry-meta">
          <div class="run-entry-meta-row">
            <div class="run-entry-times-inline">
              <span class="run-entry-time">
                <span class="run-entry-meta-label">Started</span>
                {{ run.startedAt }}
              </span>
            </div>
            <div class="run-entry-duration">
              {{ runDurationText(run.raw) }}
            </div>
          </div>
        </div>

        <div class="run-entry-footer">
          <div class="run-entry-footer-content">
            <div v-if="run.runtimeUrl" class="run-entry-detail-row">
              <div class="run-entry-detail-label">Runtime source URI</div>
              <div class="run-entry-detail-value">
                <div class="run-entry-detail-linkwrap">
                  <a
                    class="text-slate-600 underline break-all hover:text-blue-700"
                    :href="run.runtimeUrl"
                    target="_blank"
                    rel="noopener"
                  >
                    {{ run.runtimeUrl }}
                  </a>
                  <v-tooltip text="Copy runtime source URI" location="bottom">
                    <template #activator="{ props: tooltipProps }">
                      <v-btn
                        v-bind="tooltipProps"
                        icon
                        variant="text"
                        size="small"
                        color="blue-grey-darken-2"
                        aria-label="Copy runtime source URI"
                        @click="$emit('copy', run.runtimeUrl)"
                      >
                        <v-icon :icon="mdiContentCopy" />
                      </v-btn>
                    </template>
                  </v-tooltip>
                </div>
              </div>
            </div>

            <div
              v-if="run.violations.length"
              class="run-entry-detail-row run-entry-violations-row"
            >
              <div class="run-entry-detail-label">Rule violations</div>
              <div class="run-entry-detail-value">
                <div class="run-entry-violations">
                  <div
                    v-for="violation in run.violations"
                    :key="violation.key"
                    class="run-entry-violation"
                  >
                    <div class="run-entry-violation-title">
                      {{ violation.datastreamName }}
                      <span class="run-entry-violation-type">
                        {{ violation.ruleTypeLabel }}
                      </span>
                    </div>
                    <div class="run-entry-violation-meta">
                      {{ violation.violationCount }} violation{{
                        violation.violationCount === 1 ? '' : 's'
                      }}
                      <span v-if="violation.firstViolationAt">
                        - First {{ violation.firstViolationAt }}
                      </span>
                      <span v-if="violation.lastViolationAt">
                        - Last {{ violation.lastViolationAt }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="run-entry-detail-row run-entry-detail-row-inline">
              <div class="run-entry-detail-inline">
                <div class="run-entry-detail-label">Copy run as URL</div>
                <v-tooltip text="Copy run as URL" location="bottom">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      v-bind="tooltipProps"
                      icon
                      variant="text"
                      size="small"
                      color="blue-grey-darken-2"
                      aria-label="Copy run as URL"
                      @click="$emit('copy-run-link', run.id)"
                    >
                      <v-icon :icon="mdiContentCopy" />
                    </v-btn>
                  </template>
                </v-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-if="!hasLoadedFullRunHistory" class="run-entry-refresh">
      <v-btn
        variant="text"
        :prepend-icon="mdiHistory"
        size="small"
        class="text-none"
        :loading="loadingFullRunHistory"
        @click="$emit('fetch-full')"
      >
        See full history
      </v-btn>
    </div>
  </template>

  <div v-else class="run-empty">No run history available yet.</div>
</template>

<script setup lang="ts">
import type { TaskRun } from '@hydroserver/client'
import { mdiContentCopy, mdiHistory } from '@mdi/js'
import TaskStatus from '@/components/Orchestration/shared/TaskStatus.vue'
import { getTaskRunStatusText as getRunStatusText } from '@/utils/orchestration/taskRunDetails'

type RunHistoryRow = {
  id: string
  domId: string
  startedAt: string
  message: string
  runtimeUrl: string | null
  violations: Array<{
    key: string
    datastreamName: string
    ruleTypeLabel: string
    violationCount: number
    firstViolationAt: string | null
    lastViolationAt: string | null
  }>
  raw: TaskRun
}

defineProps<{
  rows: RunHistoryRow[]
  showLoading: boolean
  hasLoadedFullRunHistory: boolean
  loadingFullRunHistory: boolean
  highlightedRunId: string | null
}>()

defineEmits<{
  (e: 'fetch-full'): void
  (e: 'copy', value: string): void
  (e: 'copy-run-link', runId: string): void
}>()

const shortId = (id: string) => {
  const value = `${id || ''}`
  if (!value) return '-'
  return value.split('-')[0] || value.slice(0, 8)
}

const formatDurationMs = (ms: number) => {
  if (!Number.isFinite(ms) || ms < 0) return '-'
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`
  const totalSeconds = Math.floor(ms / 1000)
  const seconds = totalSeconds % 60
  const totalMinutes = Math.floor(totalSeconds / 60)
  const minutes = totalMinutes % 60
  const totalHours = Math.floor(totalMinutes / 60)
  const hours = totalHours % 24
  const days = Math.floor(totalHours / 24)

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

const runDurationText = (run?: TaskRun | null) => {
  if (!run) return 'Duration -'
  if (run.status === 'PENDING') return 'Queued'
  if (run.status === 'STARTED') return 'Running'
  const start = run.startedAt ? new Date(run.startedAt as any).getTime() : NaN
  const end = run.finishedAt ? new Date(run.finishedAt as any).getTime() : NaN
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 'Duration -'
  return `Duration ${formatDurationMs(end - start)}`
}
</script>

<style scoped>
.run-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
  color: #475569;
  font-size: 13px;
}

.run-empty {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
  font-size: 13px;
}

.run-entry {
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #ebebeb;
}

.run-entry-top {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 16px;
  padding: 12px 14px 8px;
}

.run-entry-top-left {
  display: flex;
  align-items: flex-start;
  flex: 0 0 auto;
}

.run-entry-runid-right {
  flex: 0 0 auto;
  margin-left: auto;
  padding-top: 2px;
  font-size: 0.75rem;
  font-weight: 700;
  color: #0e7490;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.run-entry-status {
  flex: 0 0 auto;
  letter-spacing: 0.01em;
}

.run-entry-summary {
  flex: 1 1 auto;
  min-width: 0;
  font-weight: 500;
  color: #475569;
  font-size: 0.88rem;
  line-height: 1.35;
  word-break: break-word;
  white-space: normal;
}

.run-entry-meta {
  padding: 8px 14px 10px;
  border-top: 1px solid #f1f5f9;
}

.run-entry-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.run-entry-times-inline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
  color: #475569;
  font-size: 0.85rem;
}

.run-entry-meta-label {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  margin-right: 6px;
  font-size: 0.68rem;
  white-space: nowrap;
}

.run-entry-duration {
  font-size: 0.78rem;
  font-weight: 700;
  color: #334155;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 2px 10px;
  white-space: nowrap;
}

.run-entry-footer {
  padding: 8px 14px 10px;
  border-top: 1px solid #f1f5f9;
}

.run-entry-footer-content {
  display: grid;
  gap: 8px;
}

.run-entry-detail-row {
  display: grid;
  grid-template-columns: minmax(160px, 190px) 1fr;
  gap: 10px;
  align-items: start;
}

.run-entry-detail-row-inline {
  grid-template-columns: 1fr;
}

.run-entry-detail-inline {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
}

.run-entry-detail-label {
  font-size: 0.7rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  white-space: nowrap;
  padding-top: 2px;
}

.run-entry-detail-value {
  display: flex;
  justify-content: flex-start;
  min-width: 0;
}

.run-entry-detail-linkwrap {
  max-width: 100%;
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: flex-start;
  gap: 8px;
}

.run-entry-violations {
  display: grid;
  gap: 8px;
  min-width: 0;
  width: 100%;
}

.run-entry-violation {
  border: 1px solid #fee2e2;
  border-radius: 6px;
  background: #fff7f7;
  padding: 8px 10px;
}

.run-entry-violation-title {
  color: #7f1d1d;
  font-size: 0.82rem;
  font-weight: 800;
  line-height: 1.25;
}

.run-entry-violation-type {
  color: #991b1b;
  font-size: 0.72rem;
  font-weight: 700;
  margin-left: 6px;
  text-transform: uppercase;
}

.run-entry-violation-meta {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.35;
  margin-top: 3px;
}

.run-entry-refresh {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.run-highlight {
  animation: runHighlightPulse 2.5s ease-out;
}

@keyframes runHighlightPulse {
  0% {
    background: rgba(255, 235, 59, 0.35);
  }
  100% {
    background: #ffffff;
  }
}

@media (max-width: 768px) {
  .run-entry-detail-row {
    grid-template-columns: 1fr;
    align-items: start;
  }
  .run-entry-detail-label {
    margin-bottom: 4px;
  }
}
</style>
