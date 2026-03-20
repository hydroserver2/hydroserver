import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TaskRun } from '@hydroserver/client'
import {
  buildTaskRunDetailSections,
  getDisplayedTaskStatus,
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
    expect(getDisplayedTaskStatus()).toBe('Unknown')
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
        status: 'RUNNING',
        result: null,
      })
    ).toBe('Run in progress.')
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
    const leanFailure: TaskRun = {
      id: 'run-0',
      status: 'SUCCESS',
      failureCount: 2,
      result: null,
    }

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
    expect(
      getDisplayedTaskStatus({
        schedule: { paused: true, nextRunAt: '2026-03-13T13:00:00Z' },
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
          nextRunAt: null,
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
          status: 'RUNNING',
          result: null,
        },
      })
    ).toBe('Pending')

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
            stage: 'EXTRACT',
            msg: 'Starting extract',
          },
          {
            timestamp: '2026-03-12T12:01:00Z',
            level: 'INFO',
            stage: 'TRANSFORM',
            message: 'Starting transform',
          },
          {
            timestamp: '2026-03-12T12:02:00Z',
            level: 'INFO',
            stage: 'LOAD',
            message: 'Starting load',
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
    ])

    const extractSection = sections[0]
    expect(extractSection?.type).toBe('lines')
    if (extractSection?.type === 'lines') {
      expect(extractSection.entries[0]).toEqual({
        timestamp: '2026-03-12T12:00:00Z',
        level: 'INFO',
        stage: 'EXTRACT',
        message: 'Starting extract',
      })
    }
  })

  it('prefers staged ETL sections over summary when structured logs exist', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      startedAt: '2026-03-12T12:00:00Z',
      finishedAt: '2026-03-12T12:05:00Z',
      result: {
        log_entries: [
          {
            timestamp: '2026-03-12T12:00:00Z',
            level: 'INFO',
            stage: 'EXTRACT',
            message: 'Starting extract',
          },
          {
            timestamp: '2026-03-12T12:00:10Z',
            level: 'INFO',
            stage: 'EXTRACT',
            message: 'Requesting data from source URI',
          },
          {
            timestamp: '2026-03-12T12:01:00Z',
            level: 'INFO',
            stage: 'TRANSFORM',
            message: 'Starting transform',
          },
          {
            timestamp: '2026-03-12T12:02:00Z',
            level: 'WARNING',
            stage: 'LOAD',
            message: 'No new observations for target-1 after filtering; skipping.',
          },
        ],
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
        'Transform',
        'Load',
      ])
    )
    expect(sections.map((section) => section.title)).toEqual([
      'Extract',
      'Transform',
      'Load',
    ])

    const summarySection = sections.find((section) => section.title === 'Summary')
    expect(summarySection).toBeUndefined()
    expect(
      sections.find((section) => section.title === 'Target results')
    ).toBeUndefined()
    expect(
      sections.find((section) => section.title === 'Runtime context')
    ).toBeUndefined()
  })

  it('shows summary only when no staged ETL logs exist', () => {
    const run: TaskRun = {
      id: 'run-1',
      status: 'SUCCESS',
      result: {
        success_count: 1,
        failure_count: 1,
        skipped_count: 0,
        values_loaded_total: 12,
      },
    }

    const sections = buildTaskRunDetailSections(run)

    expect(sections).toEqual([
      {
        title: 'Summary',
        type: 'lines',
        entries: expect.arrayContaining([
          { level: undefined, message: 'Values loaded: 12' },
          { level: undefined, message: 'Successful targets: 1' },
          { level: 'FAILED', message: 'Failed targets: 1' },
          { level: undefined, message: 'Skipped targets: 0' },
        ]),
      },
    ])
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
