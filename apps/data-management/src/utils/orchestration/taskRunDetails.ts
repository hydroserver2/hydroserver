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

function parseCronField(
  field: string,
  min: number,
  max: number
): Set<number> | null {
  const values = new Set<number>()
  const parts = field.split(',').map((part) => part.trim())
  if (!parts.length || parts.some((part) => !part)) return null

  for (const part of parts) {
    const [rangePart, stepPart] = part.split('/')
    const step = stepPart ? Number(stepPart) : 1
    if (!Number.isInteger(step) || step < 1) return null

    let start = min
    let end = max
    if (rangePart !== '*') {
      if (rangePart.includes('-')) {
        const [rawStart, rawEnd] = rangePart.split('-').map(Number)
        start = rawStart
        end = rawEnd
      } else {
        start = Number(rangePart)
        end = start
      }
    }

    if (
      !Number.isInteger(start) ||
      !Number.isInteger(end) ||
      start < min ||
      end > max ||
      start > end
    ) {
      return null
    }

    for (let value = start; value <= end; value += step) values.add(value)
  }

  return values
}

function parseCronDayOfWeek(field: string) {
  const values = parseCronField(field, 0, 7)
  if (!values) return null
  if (values.has(7)) {
    values.add(0)
    values.delete(7)
  }
  return values
}

const matchesCron = (
  date: Date,
  fields: {
    minutes: Set<number>
    hours: Set<number>
    daysOfMonth: Set<number>
    months: Set<number>
    daysOfWeek: Set<number>
  }
) =>
  fields.minutes.has(date.getMinutes()) &&
  fields.hours.has(date.getHours()) &&
  fields.daysOfMonth.has(date.getDate()) &&
  fields.months.has(date.getMonth() + 1) &&
  fields.daysOfWeek.has(date.getDay())

const inferCrontabNextRunAt = (task?: TaskStatusLike | null) => {
  const schedule = task?.schedule
  if (!schedule?.crontab) return null

  const parts = schedule.crontab.trim().split(/\s+/)
  if (parts.length !== 5) return null

  const minutes = parseCronField(parts[0], 0, 59)
  const hours = parseCronField(parts[1], 0, 23)
  const daysOfMonth = parseCronField(parts[2], 1, 31)
  const months = parseCronField(parts[3], 1, 12)
  const daysOfWeek = parseCronDayOfWeek(parts[4])

  if (!minutes || !hours || !daysOfMonth || !months || !daysOfWeek) return null

  const startDate = parseDate(schedule.startTime)
  const now = new Date()
  const base =
    startDate && startDate.getTime() > now.getTime() ? startDate : now
  const candidate = new Date(base)
  candidate.setSeconds(0, 0)
  if (candidate.getTime() < base.getTime()) {
    candidate.setMinutes(candidate.getMinutes() + 1)
  }

  const maxMinutesToSearch = 366 * 24 * 60
  for (let offset = 0; offset <= maxMinutesToSearch; offset += 1) {
    if (
      matchesCron(candidate, {
        minutes,
        hours,
        daysOfMonth,
        months,
        daysOfWeek,
      })
    ) {
      return candidate
    }
    candidate.setMinutes(candidate.getMinutes() + 1)
  }

  return null
}

const inferIntervalNextRunAt = (task?: TaskStatusLike | null) => {
  const schedule = task?.schedule
  if (!schedule?.interval || !schedule.intervalPeriod) return null

  const intervalMsByPeriod: Record<string, number> = {
    minutes: 60_000,
    hours: 3_600_000,
    days: 86_400_000,
  }
  const unitMs = intervalMsByPeriod[schedule.intervalPeriod]
  if (!unitMs) return null

  const latestRun = task?.latestRun
  const baseDate =
    parseDate(latestRun?.startedAt) ??
    parseDate(latestRun?.finishedAt) ??
    parseDate(schedule.startTime)
  if (!baseDate) return null

  return new Date(baseDate.getTime() + schedule.interval * unitMs)
}

export const getTaskNextRunAt = (task?: TaskStatusLike | null) =>
  parseDate(task?.schedule?.nextRunAt) ??
  inferIntervalNextRunAt(task) ??
  inferCrontabNextRunAt(task)

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
