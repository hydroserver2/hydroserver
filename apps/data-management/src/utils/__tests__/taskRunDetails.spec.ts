import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TaskRun } from '@hydroserver/client'
import {
  getDisplayedTaskStatus,
  getMonitoringRunViolations,
  getMonitoringRulesViolated,
  getTaskNextRunAt,
  getTaskRunMessage,
  getTaskRunResult,
  getTaskRunRuntimeUrl,
  getTaskRunStatusText,
  getTaskStatusText,
  taskRunHasFailures,
} from '../orchestration/taskRunDetails'

describe('task run detail helpers', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('returns safe defaults for empty inputs', () => {
    expect(getTaskRunResult()).toEqual({})
    expect(getTaskRunMessage()).toBe('–')
    expect(getTaskRunRuntimeUrl()).toBeNull()
    expect(getMonitoringRunViolations()).toEqual([])
    expect(getMonitoringRulesViolated()).toBe(0)
    expect(taskRunHasFailures()).toBe(false)
    expect(getTaskRunStatusText()).toBe('Unknown')
    expect(getTaskStatusText()).toBe('Unknown')
    expect(getDisplayedTaskStatus()).toBe('Unknown')
    expect(getTaskNextRunAt()).toBeNull()
  })

  it('prefers message aliases and runtime url aliases from raw ETL payloads', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        summary: 'Summary text',
        runtime_url: 'https://example.com/runtime.csv',
      },
    }

    expect(getTaskRunMessage(run)).toBe('Summary text')
    expect(getTaskRunRuntimeUrl(run)).toBe('https://example.com/runtime.csv')
  })

  it('prefers a direct run message before reading the result payload', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      message: 'Values loaded: 42',
      result: {
        summary: 'Summary text',
      },
    }

    expect(getTaskRunMessage(run)).toBe('Values loaded: 42')
  })

  it('falls back to status text when run messages are unavailable', () => {
    expect(
      getTaskRunMessage({
        id: 'run-1',
        status: 'SUCCESS',
        result: null,
      })
    ).toBe('Run completed successfully.')

    expect(
      getTaskRunMessage({
        id: 'run-2',
        status: 'STARTED',
        result: null,
      })
    ).toBe('Run in progress.')

    expect(
      getTaskRunMessage({
        id: 'run-3',
        status: 'PENDING',
        result: null,
      })
    ).toBe('Run queued.')
  })

  it('reads the runtime source URI from nested runtime variables', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        runtime_variables: {
          extractor: {
            source_uri: 'https://example.com/runtime.csv',
          },
        },
      },
    }

    expect(getTaskRunRuntimeUrl(run)).toBe('https://example.com/runtime.csv')
  })

  it('prefers rendered extractor runtime URI over configured template aliases', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        runtime_source_uri: 'https://example.com/{site}/template.csv',
        runtime_variables: {
          extractor: {
            source_uri: 'https://example.com/site-1/runtime.csv',
          },
        },
      },
    }

    expect(getTaskRunRuntimeUrl(run)).toBe(
      'https://example.com/site-1/runtime.csv'
    )
  })

  it('treats failure status as failed', () => {
    expect(
      taskRunHasFailures({
        id: 'run-1',
        status: 'FAILURE',
        result: null,
      })
    ).toBe(true)
  })

  it('uses failure counts and target status to detect failed runs', () => {
    const leanFailure = {
      id: 'run-0',
      status: 'SUCCESS',
      failureCount: 2,
      result: null,
    } as any as TaskRun

    const countedFailure: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        failure_count: 1,
      },
    }

    const targetFailure: TaskRun = {
      id: 'run-2',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        targetResults: {
          'target-1': {
            status: 'failed',
          },
        },
      },
    }

    const success: TaskRun = {
      id: 'run-3',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        failureCount: 0,
        target_results: {
          'target-1': {
            status: 'success',
          },
        },
      },
    }

    expect(taskRunHasFailures(leanFailure)).toBe(true)
    expect(taskRunHasFailures(countedFailure)).toBe(true)
    expect(taskRunHasFailures(targetFailure)).toBe(true)
    expect(taskRunHasFailures(success)).toBe(false)
  })

  it('uses monitoring rule violations to detect attention states', () => {
    const run: TaskRun = {
      id: 'run-monitoring',
      status: 'SUCCESS',
      result: {
        rules_violated: 2,
        violations: [
          {
            rule_id: 'rule-1',
            datastream_id: 'datastream-1',
            rule_type: 'range',
            violation_count: 3,
            first_violation_at: '2026-03-12T12:00:00Z',
            last_violation_at: '2026-03-12T14:00:00Z',
          },
          {
            ruleId: 'rule-2',
            datastreamId: 'datastream-2',
            ruleType: 'missing_data',
            violationCount: 1,
            firstViolationAt: '2026-03-13T12:00:00Z',
            lastViolationAt: null,
          },
        ],
      },
    }

    expect(getMonitoringRulesViolated(run)).toBe(2)
    expect(getMonitoringRunViolations(run)).toEqual([
      {
        ruleId: 'rule-1',
        datastreamId: 'datastream-1',
        ruleType: 'range',
        violationCount: 3,
        firstViolationAt: '2026-03-12T12:00:00Z',
        lastViolationAt: '2026-03-12T14:00:00Z',
      },
      {
        ruleId: 'rule-2',
        datastreamId: 'datastream-2',
        ruleType: 'missing_data',
        violationCount: 1,
        firstViolationAt: '2026-03-13T12:00:00Z',
        lastViolationAt: null,
      },
    ])
    expect(taskRunHasFailures(run)).toBe(true)
    expect(getTaskRunStatusText(run)).toBe('Needs attention')
  })

  it('maps task run statuses for UI display', () => {
    expect(
      getTaskRunStatusText({
        id: 'run-1',
        status: 'SUCCESS',
        result: {
          failureCount: 0,
        },
      })
    ).toBe('OK')

    expect(
      getTaskRunStatusText({
        id: 'run-2',
        status: 'STARTED',
        result: {},
      })
    ).toBe('Pending')

    expect(
      getTaskRunStatusText({
        id: 'run-2b',
        status: 'PENDING',
        result: {},
      })
    ).toBe('Pending')

    expect(
      getTaskRunStatusText({
        id: 'run-3',
        status: 'SUCCESS',
        result: {
          failure_count: 1,
        },
      })
    ).toBe('Needs attention')

    expect(
      getTaskRunStatusText({
        id: 'run-4',
        status: 'RETRYING',
        result: {},
      } as TaskRun)
    ).toBe('Unknown')
  })

  it('computes task status for schedule and run combinations', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-13T12:00:00Z'))

    const okRun: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      result: {
        failureCount: 0,
      },
    }

    expect(getTaskStatusText({})).toBe('Pending')
    expect(getTaskStatusText({ latestRun: okRun })).toBe('OK')
    expect(
      getTaskStatusText({
        latestRun: {
          id: 'run-pending',
          status: 'PENDING',
          result: null,
        },
      })
    ).toBe('Pending')
    expect(
      getDisplayedTaskStatus({
        schedule: { paused: true, nextRunAt: '2026-03-13T13:00:00Z' },
        latestRun: okRun,
      })
    ).toBe('Loading paused')
    expect(
      getDisplayedTaskStatus({
        schedule: { enabled: false, nextRunAt: '2026-03-13T13:00:00Z' },
        latestRun: okRun,
      })
    ).toBe('Loading paused')
    expect(getTaskStatusText({ schedule: { paused: false } })).toBe('Pending')
    expect(
      getTaskStatusText({
        schedule: { paused: false, nextRunAt: '2026-03-13T11:00:00Z' },
        latestRun: okRun,
      })
    ).toBe('Behind schedule')
    expect(
      getTaskStatusText({
        schedule: { paused: false, nextRunAt: '2026-03-13T13:00:00Z' },
        latestRun: okRun,
      })
    ).toBe('OK')
    expect(
      getTaskStatusText({
        schedule: { paused: false, nextRunAt: 'not-a-date' },
        latestRun: okRun,
      })
    ).toBe('Unknown')
    expect(
      getTaskStatusText({
        schedule: { paused: false, nextRunAt: '2026-03-13T13:00:00Z' },
        latestRun: {
          id: 'run-2',
          status: 'SUCCESS',
          result: { failure_count: 1 },
        },
      })
    ).toBe('Needs attention')
    expect(
      getTaskStatusText({
        schedule: {
          paused: false,
          nextRunAt: '2026-02-24T12:00:00Z',
          interval: 1,
          intervalPeriod: 'days',
        },
        latestRun: {
          id: 'run-3',
          status: 'SUCCESS',
          startedAt: '2026-02-23T12:00:00Z',
          result: { failureCount: 0 },
        },
      })
    ).toBe('Behind schedule')
    expect(
      getTaskStatusText({
        schedule: {
          paused: false,
          nextRunAt: '2026-03-13T11:00:00Z',
        },
        latestRun: {
          id: 'run-4',
          status: 'STARTED',
          result: null,
        },
      })
    ).toBe('Pending')

    vi.useRealTimers()
  })

  it('returns null when the backend provides no nextRunAt', () => {
    const next = getTaskNextRunAt({
      schedule: {
        nextRunAt: null,
        interval: 2,
        intervalPeriod: 'hours',
      },
      latestRun: {
        id: 'run-interval',
        status: 'SUCCESS',
        startedAt: '2026-03-13T10:00:00Z',
        result: { failureCount: 0 },
      },
    })

    expect(next).toBeNull()
  })

  it('returns the backend-provided nextRunAt when present', () => {
    const next = getTaskNextRunAt({
      schedule: {
        nextRunAt: '2026-03-14T08:30:00Z',
        interval: 2,
        intervalPeriod: 'hours',
      },
      latestRun: {
        id: 'run-interval',
        status: 'SUCCESS',
        startedAt: '2026-03-13T10:00:00Z',
        result: { failureCount: 0 },
      },
    })

    expect(next?.toISOString()).toBe('2026-03-14T08:30:00.000Z')
  })
})
