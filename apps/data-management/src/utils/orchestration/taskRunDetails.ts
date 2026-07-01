import { StatusType, TaskRun } from '@hydroserver/client'

type TaskStatusLike = {
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

const getTargetResults = (result: TaskRunResultLike) =>
  asObject(result.targetResults ?? result.target_results)

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

export const getMonitoringRulesViolated = (run?: TaskRun | null) => {
  const result = getTaskRunResult(run)
  const count = firstNumber(result.rulesViolated, result.rules_violated)
  if (count !== undefined) return count

  const violations = result.violations
  return Array.isArray(violations) ? violations.length : 0
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

export const taskRunHasFailures = (run?: TaskRun | null) => {
  if (!run) return false
  if (run.status === 'FAILURE') return true

  const result = getTaskRunResult(run)
  if (getMonitoringRulesViolated(run) > 0) return true

  const failureCount = firstNumber(
    (run as any).failureCount,
    result.failureCount,
    result.failure_count
  )
  if (failureCount !== undefined) return failureCount > 0

  const targetResults = getTargetResults(result)
  if (!targetResults) return false

  return Object.values(targetResults).some((target) => {
    const targetRecord = asObject(target)
    return firstString(targetRecord?.status)?.toLowerCase() === 'failed'
  })
}

export const getTaskRunStatusText = (run?: TaskRun | null): StatusType => {
  if (!run) return 'Unknown'
  if (taskRunHasFailures(run)) return 'Needs attention'
  if (run.status === 'SUCCESS') return 'OK'
  if (run.status === 'PENDING' || run.status === 'STARTED') return 'Pending'
  return 'Unknown'
}

export const getTaskStatusText = (task?: TaskStatusLike | null): StatusType => {
  if (!task) return 'Unknown'

  const { latestRun, schedule } = task
  if (!schedule) {
    if (!latestRun) return 'Pending'
    if (latestRun.status === 'PENDING' || latestRun.status === 'STARTED') {
      return 'Pending'
    }
    return taskRunHasFailures(latestRun) ? 'Needs attention' : 'OK'
  }

  if (!latestRun) return 'Pending'
  if (taskRunHasFailures(latestRun)) return 'Needs attention'
  if (latestRun.status === 'PENDING' || latestRun.status === 'STARTED') {
    return 'Pending'
  }

  const next = getTaskNextRunAt(task)
  if (next) {
    return next.getTime() < Date.now() ? 'Behind schedule' : 'OK'
  }

  return 'Unknown'
}

export const getDisplayedTaskStatus = (
  task?: TaskStatusLike | null
): StatusType => {
  const status = getTaskStatusText(task)
  const isPaused =
    task?.schedule?.paused === true || task?.schedule?.enabled === false
  if (isPaused && status !== 'Needs attention') {
    return 'Loading paused'
  }
  return status
}
