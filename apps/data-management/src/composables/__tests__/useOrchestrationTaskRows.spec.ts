import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useOrchestrationTaskRows } from '../orchestration/useOrchestrationTaskRows'

describe('useOrchestrationTaskRows', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  const buildRows = () =>
    useOrchestrationTaskRows({
      activeTab: ref('ingestion'),
      workspaceTasks: ref([
        {
          id: 'etl-1',
          name: 'CSV load',
          dataConnectionId: 'dc-1',
          mappingCount: 1,
          latestRun: {
            id: 'run-1',
            status: 'SUCCESS',
            startedAt: '2025-01-02T00:00:00Z',
          },
          schedule: {
            enabled: true,
            nextRunAt: '2025-01-03T00:00:00Z',
          },
        },
      ] as any),
      dataProductTasks: ref([
        {
          id: 'dp-1',
          name: 'Rating curve',
          monitoringSiteId: 'monitoringSite-2',
          latestRun: null,
          schedule: null,
          transformationTypes: ['rating_curve'],
        },
      ] as any),
      monitoringTasks: ref([
        {
          id: 'mon-1',
          name: 'Quality check',
          monitoringSiteId: 'monitoringSite-3',
          latestRun: {
            status: 'FAILURE',
            result: { rulesViolated: 2 },
          },
          schedule: null,
          ruleTypeCounts: { range: 2, spike_check: 1 },
        },
      ] as any),
      runNowTriggeredByTaskId: { 'etl-1': true },
    })

  it('builds ETL rows with data connection, run, and schedule metadata', () => {
    const rows = buildRows()
    const row = rows.etlTaskRows.value[0]

    expect(row).toMatchObject({
      id: 'etl-1',
      kind: 'etl',
      name: 'CSV load',
      dataConnectionId: 'dc-1',
      monitoringSiteId: null,
      userClickedRunNow: true,
      taskType: null,
      noWorkWarning: null,
      lastRunAt: '2025-01-02T00:00:00Z',
      nextRunAt: '2025-01-03T00:00:00Z',
    })
    expect(row.lastRun).not.toBe('-')
    expect(row.nextRun).not.toBe('-')
  })

  it('builds data product and monitoring rows with derived summaries', () => {
    const rows = buildRows()

    expect(rows.dataProductTaskRows.value[0]).toMatchObject({
      id: 'dp-1',
      kind: 'dataProduct',
      monitoringSiteId: 'monitoringSite-2',
      taskType: 'Rating curve',
      noWorkWarning: null,
    })
    expect(rows.monitoringTaskRows.value[0]).toMatchObject({
      id: 'mon-1',
      kind: 'monitoring',
      monitoringSiteId: 'monitoringSite-3',
      statusName: 'Needs attention',
      statusSort: 'Needs attention',
      qualityRuleCount: 3,
      monitoringRulesViolated: 2,
      noWorkWarning: null,
    })
  })

  it('classifies derivation transformations as derivation regardless of input count', () => {
    const rows = useOrchestrationTaskRows({
      activeTab: ref('aggregation'),
      workspaceTasks: ref([]),
      dataProductTasks: ref([
        {
          id: 'dp-expr',
          name: 'Unit conversion',
          monitoringSiteId: 'monitoringSite-4',
          latestRun: null,
          schedule: null,
          transformationTypes: ['derivation'],
        },
        {
          id: 'dp-combined',
          name: 'Combined flow',
          monitoringSiteId: 'monitoringSite-4',
          latestRun: null,
          schedule: null,
          transformationTypes: ['derivation'],
        },
      ] as any),
      monitoringTasks: ref([]),
      runNowTriggeredByTaskId: {},
    })

    expect(rows.dataProductTaskRows.value[0].taskType).toBe('Derivation')
    expect(rows.dataProductTaskRows.value[1].taskType).toBe('Derivation')
  })

  it('flags tasks that have no configured work', () => {
    const rows = useOrchestrationTaskRows({
      activeTab: ref('ingestion'),
      workspaceTasks: ref([
        {
          id: 'etl-empty',
          name: 'Empty import',
          dataConnectionId: 'dc-1',
          mappingCount: 0,
          latestRun: null,
          schedule: null,
        },
      ] as any),
      dataProductTasks: ref([
        {
          id: 'dp-empty',
          name: 'Empty product',
          monitoringSiteId: 'monitoringSite-2',
          latestRun: null,
          schedule: null,
          transformationTypes: [],
        },
      ] as any),
      monitoringTasks: ref([
        {
          id: 'mon-empty',
          name: 'Empty quality task',
          monitoringSiteId: 'monitoringSite-3',
          latestRun: null,
          schedule: null,
          ruleTypeCounts: {},
        },
      ] as any),
      runNowTriggeredByTaskId: {},
    })

    expect(rows.etlTaskRows.value[0].noWorkWarning).toEqual({
      label: 'No mappings',
      message:
        "This task has no mappings configured, so running it won't do anything.",
    })
    expect(rows.dataProductTaskRows.value[0].noWorkWarning).toEqual({
      label: 'No mappings',
      message:
        "This task has no transformations configured, so running it won't do anything.",
    })
    expect(rows.monitoringTaskRows.value[0].noWorkWarning).toEqual({
      label: 'No rules',
      message:
        "This quality task has no rules configured, so running it won't do anything.",
    })
  })

  it('displays backend-provided next run times for scheduled data product rows', () => {
    const rows = useOrchestrationTaskRows({
      activeTab: ref('aggregation'),
      workspaceTasks: ref([]),
      dataProductTasks: ref([
        {
          id: 'dp-interval',
          name: 'Scheduled rating curve',
          monitoringSiteId: 'monitoringSite-2',
          latestRun: null,
          schedule: {
            enabled: true,
            startTime: '2026-03-13T13:00:00Z',
            nextRunAt: '2026-03-14T13:00:00Z',
            crontab: null,
            interval: 1,
            intervalPeriod: 'days',
          },
          transformationTypes: ['rating_curve'],
        },
      ] as any),
      monitoringTasks: ref([]),
      runNowTriggeredByTaskId: {},
    })

    const row = rows.dataProductTaskRows.value[0]
    expect(row.nextRunAt).toBe('2026-03-14T13:00:00Z')
    expect(row.nextRun).not.toBe('-')
  })

  it('displays completed monitoring runs as OK instead of Pending', () => {
    const rows = useOrchestrationTaskRows({
      activeTab: ref('quality'),
      workspaceTasks: ref([]),
      dataProductTasks: ref([]),
      monitoringTasks: ref([
        {
          id: 'mon-ok',
          name: 'Quality OK',
          monitoringSiteId: 'monitoringSite-1',
          latestRun: {
            id: 'run-ok',
            status: 'SUCCESS',
            result: { rulesViolated: 0 },
            startedAt: '2026-03-13T12:00:00Z',
          },
          schedule: null,
          ruleTypeCounts: {},
        },
      ] as any),
      runNowTriggeredByTaskId: {},
    })

    expect(rows.monitoringTaskRows.value[0]).toMatchObject({
      statusName: 'OK',
      statusSort: 'OK',
      lastRunAt: '2026-03-13T12:00:00Z',
    })
  })

  it('switches active rows and sorts by the selected field', () => {
    const rows = buildRows()

    expect(rows.activeTaskRows.value.map((row) => row.id)).toEqual(['etl-1'])

    rows.toggleSort('nextRunAt')
    expect(rows.sortKey.value).toBe('nextRunAt')
    expect(rows.sortDir.value).toBe('asc')
    rows.toggleSort('nextRunAt')
    expect(rows.sortDir.value).toBe('desc')

    expect(
      rows.sortRows([
        { name: 'B', nextRunAt: null } as any,
        { name: 'A', nextRunAt: '2025-01-01T00:00:00Z' } as any,
      ])
    ).toEqual([
      { name: 'B', nextRunAt: null },
      { name: 'A', nextRunAt: '2025-01-01T00:00:00Z' },
    ])

    rows.toggleSort('taskType')
    expect(rows.sortKey.value).toBe('taskType')
    expect(
      rows
        .sortRows([
          { name: 'Mean stage', taskType: 'Aggregation' } as any,
          { name: 'Curve output', taskType: 'Rating curve' } as any,
          { name: 'Combined flow', taskType: 'Derivation' } as any,
        ])
        .map((row) => row.taskType)
    ).toEqual(['Aggregation', 'Derivation', 'Rating curve'])
  })
})
