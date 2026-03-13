import { StatusType, TaskRun } from '@hydroserver/client'

type TaskStatusLike = {
  latestRun?: TaskRun | null
  schedule?: {
    paused?: boolean | null
    nextRunAt?: string | null
    startTime?: string | null
    interval?: number | null
    intervalPeriod?: string | null
  } | null
}

type TaskRunResultLike = Record<string, unknown>

export type TaskRunDetailEntry = {
  timestamp?: string
  level?: string
  message: string
}

export type TaskRunDetailSection =
  | {
      title: string
      type: 'lines'
      entries: TaskRunDetailEntry[]
    }
  | {
      title: string
      type: 'text'
      text: string
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

export const prettyJson = (value: unknown) => {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

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
      : run.status === 'RUNNING'
        ? 'Run in progress.'
        : run.status === 'FAILURE' || run.status === 'INCOMPLETE'
          ? 'Run failed.'
          : '–')
  )
}

export const getTaskRunRuntimeUrl = (run?: TaskRun | null) => {
  const result = getTaskRunResult(run)
  const extractorRuntime = asObject(getRuntimeVariables(result)?.extractor)

  return (
    firstString(
      result.runtimeSourceUri,
      result.runtime_source_uri,
      result.runtimeUrl,
      result.runtime_url,
      extractorRuntime?.sourceUri,
      extractorRuntime?.source_uri
    ) ?? null
  )
}

export const taskRunHasFailures = (run?: TaskRun | null) => {
  if (!run) return false
  if (run.status === 'FAILURE' || run.status === 'INCOMPLETE') return true

  const result = getTaskRunResult(run)
  const failureCount = firstNumber(
    run.failureCount,
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
  if (run.status === 'RUNNING') return 'Pending'
  return 'Unknown'
}

export const getTaskStatusText = (task?: TaskStatusLike | null): StatusType => {
  if (!task) return 'Unknown'

  const { latestRun, schedule } = task
  if (!schedule) {
    if (!latestRun) return 'Pending'
    return taskRunHasFailures(latestRun) ? 'Needs attention' : 'OK'
  }

  if (!latestRun) return 'Pending'
  if (taskRunHasFailures(latestRun)) return 'Needs attention'
  if (latestRun.status === 'RUNNING') return 'Pending'

  const next = parseDate(schedule.nextRunAt) ?? inferIntervalNextRunAt(task)
  if (next) {
    return next.getTime() < Date.now() ? 'Behind schedule' : 'OK'
  }

  return 'Unknown'
}

export const getDisplayedTaskStatus = (
  task?: TaskStatusLike | null
): StatusType => {
  const status = getTaskStatusText(task)
  if (task?.schedule?.paused && status !== 'Needs attention') {
    return 'Loading paused'
  }
  return status
}

const normalizeLogEntries = (result: TaskRunResultLike): TaskRunDetailEntry[] => {
  const logEntries = result.logEntries ?? result.log_entries
  if (Array.isArray(logEntries)) {
    return logEntries.map((entry) => {
      const record = asObject(entry)
      if (!record) return { message: String(entry) }

      return {
        timestamp: firstString(record.timestamp, record.time) ?? '',
        level: firstString(record.level, record.levelname) ?? '',
        message:
          firstString(record.message, record.msg) ?? prettyJson(record),
      }
    })
  }

  if (typeof result.logs === 'string') {
    return result.logs
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const match = line.match(/^(\S+)\s+([A-Z]+)\s+(.*)$/)
        if (match) {
          return {
            timestamp: match[1],
            level: match[2],
            message: match[3],
          }
        }
        return { message: line }
      })
  }

  return []
}

const stageFromMessage = (message: string) => {
  const lower = message.toLowerCase()
  if (lower.startsWith('etl task')) return 'Extract'
  if (lower.startsWith('transformer timestamp')) return 'Extract'
  if (lower.startsWith('runtime variables resolved')) return 'Extract'
  if (lower.startsWith('task variables resolved')) return 'Extract'
  if (lower.startsWith('resolved runtime source uri')) return 'Extract'
  if (lower.startsWith('extractor returned payload')) return 'Extract'
  if (lower.includes('starting extract')) return 'Extract'
  if (lower.includes('starting transform')) return 'Transform'
  if (lower.includes('starting load')) return 'Load'
  if (lower.includes('resolving runtime var')) return 'Extract'
  if (lower.includes('requesting data from')) return 'Extract'
  if (lower.includes('standardized dataframe')) return 'Transform'
  if (lower.includes('uploading')) return 'Load'
  return null
}

const buildSummaryEntries = (result: TaskRunResultLike): TaskRunDetailEntry[] => {
  const rows = [
    ['Values loaded', firstNumber(result.valuesLoadedTotal, result.values_loaded_total)],
    ['Successful targets', firstNumber(result.successCount, result.success_count)],
    ['Failed targets', firstNumber(result.failureCount, result.failure_count)],
    ['Skipped targets', firstNumber(result.skippedCount, result.skipped_count)],
    [
      'Earliest timestamp',
      firstString(result.earliestTimestamp, result.earliest_timestamp),
    ],
    ['Latest timestamp', firstString(result.latestTimestamp, result.latest_timestamp)],
  ]

  return rows
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([label, value]) => ({
      level:
        label === 'Failed targets' && Number(value) > 0 ? 'FAILED' : undefined,
      message: `${label}: ${value}`,
    }))
}

const buildTargetResultEntries = (
  result: TaskRunResultLike
): TaskRunDetailEntry[] => {
  const targetResults = getTargetResults(result)
  if (!targetResults) return []

  return Object.entries(targetResults).map(([targetId, target]) => {
    const targetRecord = asObject(target) ?? {}
    const status = firstString(targetRecord.status)?.toUpperCase() ?? 'UNKNOWN'
    const valuesLoaded = firstNumber(
      targetRecord.valuesLoaded,
      targetRecord.values_loaded
    )
    const error = firstString(targetRecord.error)
    const earliest = firstString(
      targetRecord.earliestTimestamp,
      targetRecord.earliest_timestamp
    )
    const latest = firstString(
      targetRecord.latestTimestamp,
      targetRecord.latest_timestamp
    )

    const details = [
      `Target ${targetId}`,
      typeof valuesLoaded === 'number' ? `${valuesLoaded} loaded` : null,
      earliest ? `first ${earliest}` : null,
      latest ? `last ${latest}` : null,
      error,
    ].filter(Boolean)

    return {
      level: status,
      message: details.join(' | '),
    }
  })
}

export const buildTaskRunDetailSections = (
  run?: TaskRun | null
): TaskRunDetailSection[] => {
  if (!run) return [{ title: 'Logs', type: 'text', text: '–' }]

  const result = getTaskRunResult(run)
  const sections: TaskRunDetailSection[] = []

  const logEntries = normalizeLogEntries(result)
  if (logEntries.length) {
    const grouped: TaskRunDetailSection[] = []
    let currentTitle = stageFromMessage(logEntries[0]?.message || '') || 'Logs'
    let currentEntries: TaskRunDetailEntry[] = []

    const pushSection = () => {
      if (currentEntries.length) {
        grouped.push({
          title: currentTitle,
          type: 'lines',
          entries: currentEntries,
        })
      }
    }

    logEntries.forEach((entry) => {
      const nextStage = stageFromMessage(entry.message || '')
      if (nextStage && nextStage !== currentTitle) {
        pushSection()
        currentTitle = nextStage
        currentEntries = []
      }
      currentEntries.push(entry)
    })

    pushSection()
    sections.push(...grouped)
  }

  const summaryEntries = buildSummaryEntries(result)
  if (summaryEntries.length) {
    sections.push({
      title: 'Summary',
      type: 'lines',
      entries: summaryEntries,
    })
  }

  const errorText = firstString(result.error)
  if (errorText) {
    sections.push({
      title: 'Error',
      type: 'text',
      text: errorText,
    })
  }

  const runtimeVariables = getRuntimeVariables(result)
  if (runtimeVariables && Object.keys(runtimeVariables).length) {
    sections.push({
      title: 'Runtime context',
      type: 'text',
      text: prettyJson(runtimeVariables),
    })
  }

  const targetResultEntries = buildTargetResultEntries(result)
  if (targetResultEntries.length) {
    sections.push({
      title: 'Target results',
      type: 'lines',
      entries: targetResultEntries,
    })
  }

  if (result.traceback) {
    sections.push({
      title: 'Traceback',
      type: 'text',
      text: String(result.traceback),
    })
  }

  const detail = { ...result }
  delete detail.logs
  delete detail.logEntries
  delete detail.log_entries
  delete detail.runtimeVariables
  delete detail.runtime_variables
  delete detail.targetResults
  delete detail.target_results
  delete detail.traceback
  delete detail.error
  delete detail.message
  delete detail.summary
  delete detail.statusMessage
  delete detail.status_message
  delete detail.failureReason
  delete detail.failure_reason
  delete detail.runtimeSourceUri
  delete detail.runtime_source_uri
  delete detail.runtimeUrl
  delete detail.runtime_url
  delete detail.successCount
  delete detail.success_count
  delete detail.failureCount
  delete detail.failure_count
  delete detail.skippedCount
  delete detail.skipped_count
  delete detail.valuesLoadedTotal
  delete detail.values_loaded_total
  delete detail.earliestTimestamp
  delete detail.earliest_timestamp
  delete detail.latestTimestamp
  delete detail.latest_timestamp

  if (Object.keys(detail).length) {
    sections.push({
      title: 'Details',
      type: 'text',
      text: prettyJson(detail),
    })
  }

  return sections.length
    ? sections
    : [{ title: 'Logs', type: 'text', text: '–' }]
}
