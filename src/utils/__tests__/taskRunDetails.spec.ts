import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TaskRun } from '@hydroserver/client'
import {
  buildTaskRunDetailSections,
  getTaskRunMessage,
  getTaskRunResult,
  getTaskRunRuntimeUrl,
  getTaskRunStatusText,
  getTaskStatusText,
  prettyJson,
  taskRunHasFailures,
} from '../orchestration/taskRunDetails'

describe('task run detail helpers', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns safe defaults for empty inputs', () => {
    expect(prettyJson(undefined)).toBe(undefined)
    expect(getTaskRunResult()).toEqual({})
    expect(getTaskRunMessage()).toBe('–')
    expect(getTaskRunRuntimeUrl()).toBeNull()
    expect(taskRunHasFailures()).toBe(false)
    expect(getTaskRunStatusText()).toBe('Unknown')
    expect(getTaskStatusText()).toBe('Unknown')
    expect(buildTaskRunDetailSections()).toEqual([
      { title: 'Logs', type: 'text', text: '–' },
    ])
  })

  it('falls back when json stringification fails', () => {
    const circular: Record<string, unknown> = {}
    circular.self = circular

    expect(prettyJson(circular)).toBe('[object Object]')
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

  it('treats failure and incomplete statuses as failed', () => {
    expect(
      taskRunHasFailures({
        id: 'run-1',
        status: 'FAILURE',
        result: null,
      })
    ).toBe(true)

    expect(
      taskRunHasFailures({
        id: 'run-2',
        status: 'INCOMPLETE',
        result: null,
      } as TaskRun)
    ).toBe(true)
  })

  it('uses failure counts and target status to detect failed runs', () => {
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

    expect(taskRunHasFailures(countedFailure)).toBe(true)
    expect(taskRunHasFailures(targetFailure)).toBe(true)
    expect(taskRunHasFailures(success)).toBe(false)
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
        status: 'RUNNING',
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
    expect(getTaskStatusText({ schedule: { paused: true }, latestRun: okRun })).toBe(
      'Loading paused'
    )
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

    vi.useRealTimers()
  })

  it('parses structured log entries and groups them by pipeline stage', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        logEntries: [
          {
            time: '2026-03-12T12:00:00Z',
            levelname: 'INFO',
            msg: 'ETL task started',
          },
          {
            timestamp: '2026-03-12T12:01:00Z',
            level: 'INFO',
            message: 'starting transform step',
          },
          'plain log line',
          {
            timestamp: '2026-03-12T12:02:00Z',
            level: 'INFO',
            message: 'starting load step',
          },
        ],
        error: 'Top-level error',
        traceback: 'Traceback body',
        extra_context: 'retained',
      },
    }

    const sections = buildTaskRunDetailSections(run)

    expect(sections.map((section) => section.title)).toEqual([
      'Extract',
      'Transform',
      'Load',
      'Error',
      'Traceback',
      'Details',
    ])

    const extractSection = sections[0]
    expect(extractSection?.type).toBe('lines')
    if (extractSection?.type === 'lines') {
      expect(extractSection.entries[0]).toEqual({
        timestamp: '2026-03-12T12:00:00Z',
        level: 'INFO',
        message: 'ETL task started',
      })
    }

    const detailsSection = sections[5]
    expect(detailsSection?.type).toBe('text')
    if (detailsSection?.type === 'text') {
      expect(detailsSection.text).toContain('extra_context')
    }
  })

  it('parses string logs, summary metrics, runtime context, and target results', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        logs: [
          '2026-03-12T12:00:00Z INFO starting extract step',
          'unstructured line',
          '2026-03-12T12:01:00Z INFO starting load step',
        ].join('\n'),
        success_count: 1,
        failure_count: 1,
        skipped_count: 0,
        values_loaded_total: 12,
        earliest_timestamp: '2026-03-01T00:00:00Z',
        latest_timestamp: '2026-03-12T00:00:00Z',
        runtime_variables: {
          extractor: {
            source_uri: 'https://example.com/runtime.csv',
          },
        },
        target_results: {
          'target-1': {
            status: 'failed',
            error: 'Unable to load target-1',
            earliest_timestamp: '2026-03-01T00:00:00Z',
            latest_timestamp: '2026-03-12T00:00:00Z',
          },
          'target-2': {
            status: 'success',
            values_loaded: 12,
          },
        },
      },
    }

    const sections = buildTaskRunDetailSections(run)

    expect(sections.map((section) => section.title)).toEqual(
      expect.arrayContaining([
        'Extract',
        'Load',
        'Summary',
        'Runtime context',
        'Target results',
      ])
    )

    const summarySection = sections.find((section) => section.title === 'Summary')
    expect(summarySection?.type).toBe('lines')
    if (summarySection?.type === 'lines') {
      expect(summarySection.entries).toEqual(
        expect.arrayContaining([
          { level: undefined, message: 'Values loaded: 12' },
          { level: undefined, message: 'Successful targets: 1' },
          { level: 'FAILED', message: 'Failed targets: 1' },
          { level: undefined, message: 'Skipped targets: 0' },
        ])
      )
    }

    const targetSection = sections.find(
      (section) => section.title === 'Target results'
    )
    expect(targetSection?.type).toBe('lines')
    if (targetSection?.type === 'lines') {
      expect(
        targetSection.entries.some(
          (entry) =>
            entry.level === 'FAILED' &&
            entry.message.includes('Unable to load target-1')
        )
      ).toBe(true)
      expect(
        targetSection.entries.some(
          (entry) =>
            entry.level === 'SUCCESS' &&
            entry.message.includes('12 loaded')
        )
      ).toBe(true)
    }
  })

  it('returns the default logs section when no displayable details exist', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      result: {},
    }

    expect(buildTaskRunDetailSections(run)).toEqual([
      { title: 'Logs', type: 'text', text: '–' },
    ])
  })
})
