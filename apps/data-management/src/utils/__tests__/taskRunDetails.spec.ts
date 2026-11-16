import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TaskRun } from '@hydroserver/client'
import {
  getMonitoringRunViolations,
  getMonitoringRulesViolated,
  getTaskNextRunAt,
  getTaskRunMessage,
  getTaskRunResult,
  getTaskRunRuntimeUrl,
  getTaskRunStatusText,
  getTaskStatusText,
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
    expect(getTaskRunStatusText()).toBe('Unknown')
    expect(getTaskStatusText()).toBe('Unknown')
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

  it('reads monitoring rule violations while displaying the backend status', () => {
    const run: TaskRun = {
      id: 'run-monitoring',
      status: 'SUCCESS',
      displayStatus: 'Violations found',
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
    expect(getTaskRunStatusText(run)).toBe('Violations found')
  })

  it('counts distinct violated rules instead of violating observations', () => {
    const run: TaskRun = {
      id: 'run-monitoring-counts',
      status: 'SUCCESS',
      displayStatus: 'Violations found',
      result: {
        rulesViolated: 3,
        violations: [
          {
            ruleType: 'range',
            violationCount: 3,
          },
        ],
      },
    }

    expect(getMonitoringRulesViolated(run)).toBe(1)
    expect(getTaskRunStatusText(run)).toBe('Violations found')
  })

  it.each([
    'OK',
    'Pending',
    'Needs attention',
    'Violations found',
    'Behind schedule',
    'Loading paused',
    'Unknown',
  ] as const)(
    'displays the backend task status %s without recalculating it',
    (status) => {
      expect(
        getTaskStatusText({
          status,
          schedule: { enabled: false, nextRunAt: '2000-01-01T00:00:00Z' },
          latestRun: {
            id: 'run',
            status: 'FAILURE',
            result: { rules_violated: 5 },
          },
        })
      ).toBe(status)
    }
  )

  it('displays backend run statuses without interpreting result payloads', () => {
    expect(
      getTaskRunStatusText({
        id: 'run',
        status: 'SUCCESS',
        displayStatus: 'OK',
        result: { failure_count: 2, rules_violated: 3 },
      })
    ).toBe('OK')
    expect(
      getTaskRunStatusText({
        id: 'run',
        status: 'SUCCESS',
        displayStatus: 'Violations found',
        result: null,
      })
    ).toBe('Violations found')
    expect(
      getTaskRunStatusText({ id: 'run', status: 'SUCCESS', result: null })
    ).toBe('Unknown')
    expect(getTaskStatusText({})).toBe('Unknown')
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
