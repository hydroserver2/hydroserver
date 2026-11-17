import { StatusType, TaskRun } from '@hydroserver/client'

type TaskStatusLike = {
  status?: StatusType
  latestRun?: TaskRun | null
  schedule?: {
    paused?: boolean | null
    enabled?: boolean | null
    nextRunAt?: string | null
    startTime?: string | null
    crontab?: string | null
    interval?: number | null
    intervalPeriod?: string | null
  } | null
}

type TaskRunResultLike = Record<string, unknown>

export type MonitoringRunViolation = {
  ruleId: string | null
  datastreamId: string | null
  ruleType: string | null
  violationCount: number
  firstViolationAt: string | null
  lastViolationAt: string | null
}

const asObject = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null

const firstString = (...values: unknown[]): string | null => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}

const firstNumber = (...values: unknown[]): number | undefined => {
  for (const value of values) {
    if (typeof value === 'number' && Number.isFinite(value)) return value
  }
  return undefined
}

const getRuntimeVariables = (result: TaskRunResultLike) =>
  asObject(result.runtimeVariables ?? result.runtime_variables)

const parseDate = (value?: string | null) => {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? null : date
}

export const getTaskNextRunAt = (task?: TaskStatusLike | null) =>
  parseDate(task?.schedule?.nextRunAt)

export const getTaskRunResult = (run?: TaskRun | null): TaskRunResultLike =>
  (asObject(run?.result) ?? {}) as TaskRunResultLike

export const getTaskRunMessage = (run?: TaskRun | null) => {
  if (!run) return '–'
  const result = getTaskRunResult(run)

  return (
    firstString(
      run.message,
      result.message,
      result.summary,
      result.statusMessage,
      result.status_message,
      result.failureReason,
      result.failure_reason,
      result.error
    ) ??
    (run.status === 'SUCCESS'
      ? 'Run completed successfully.'
      : run.status === 'PENDING'
        ? 'Run queued.'
        : run.status === 'STARTED' || run.status === 'RUNNING'
          ? 'Run in progress.'
          : run.status === 'FAILURE'
            ? 'Run failed.'
            : '–')
  )
}

export const getTaskRunRuntimeUrl = (run?: TaskRun | null) => {
  const result = getTaskRunResult(run)
  const extractorRuntime = asObject(getRuntimeVariables(result)?.extractor)

  return (
    firstString(
      extractorRuntime?.sourceUri,
      extractorRuntime?.source_uri,
      result.runtimeSourceUri,
      result.runtime_source_uri,
      result.runtimeUrl,
      result.runtime_url
    ) ?? null
  )
}

export const getMonitoringRunViolations = (
  run?: TaskRun | null
): MonitoringRunViolation[] => {
  const result = getTaskRunResult(run)
  const violations = Array.isArray(result.violations) ? result.violations : []

  return violations
    .map((entry) => asObject(entry))
    .filter((entry): entry is Record<string, unknown> => !!entry)
    .map((entry) => ({
      ruleId: firstString(entry.ruleId, entry.rule_id),
      datastreamId: firstString(entry.datastreamId, entry.datastream_id),
      ruleType: firstString(entry.ruleType, entry.rule_type),
      violationCount:
        firstNumber(entry.violationCount, entry.violation_count) ?? 0,
      firstViolationAt: firstString(
        entry.firstViolationAt,
        entry.first_violation_at
      ),
      lastViolationAt: firstString(
        entry.lastViolationAt,
        entry.last_violation_at
      ),
    }))
}

export const countDistinctMonitoringViolationRules = (
  violations: MonitoringRunViolation[]
) =>
  new Set(
    violations.map((violation, index) => {
      if (violation.ruleId) return violation.ruleId
      const compositeKey = [violation.datastreamId, violation.ruleType]
        .filter(Boolean)
        .join(':')
      return compositeKey || `violation-${index}`
    })
  ).size

export const getMonitoringRulesViolated = (run?: TaskRun | null) => {
  const violations = getMonitoringRunViolations(run)
  if (violations.length) {
    return countDistinctMonitoringViolationRules(violations)
  }

  const result = getTaskRunResult(run)
  return firstNumber(result.rulesViolated, result.rules_violated) ?? 0
}

// Display statuses are provided by the API; result details and the browser's
// clock must not change how tasks are classified.
export const getTaskRunStatusText = (run?: TaskRun | null): StatusType =>
  run?.displayStatus ?? 'Unknown'

export const getTaskStatusText = (task?: TaskStatusLike | null): StatusType =>
  task?.status ?? 'Unknown'
