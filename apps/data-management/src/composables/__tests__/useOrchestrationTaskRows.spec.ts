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
          dataConnection: { id: 'dc-1' },
          latestRun: {
            id: 'run-1',
            status: 'SUCCESS',
            startedAt: '2025-01-02T00:00:00Z',
          },
          schedule: {
            enabled: true,
            nextRunAt: '2025-01-03T00:00:00Z',
          },
          mappings: [{ targetDatastream: { id: 'ds-1' } }],
        },
      ] as any),
      dataProductTasks: ref([
        {
          id: 'dp-1',
          name: 'Rating curve',
          thing: { id: 'thing-2' },
          latestRun: null,
          schedule: null,
          ratingCurveTransformations: [{}],
        },
      ] as any),
      monitoringTasks: ref([
        {
          id: 'mon-1',
          name: 'Quality check',
          thing: { id: 'thing-3' },
          latestRun: {
            status: 'FAILURE',
            result: { rulesViolated: 2 },
          },
          schedule: null,
          monitoredDatastreams: [
            {
              rules: [
                { ruleType: 'RANGE_CHECK' },
                { ruleType: 'RANGE_CHECK' },
                { ruleType: 'SPIKE_CHECK' },
              ],
            },
          ],
        },
      ] as any),
      datastreamThingByDatastreamId: ref({ 'ds-1': 'thing-1' }),
      runNowTriggeredByTaskId: { 'etl-1': true },
    })

  it('builds ETL rows with data connection, site, run, and schedule metadata', () => {
    const rows = buildRows()
    const row = rows.etlTaskRows.value[0]

    expect(row).toMatchObject({
      id: 'etl-1',
      kind: 'etl',
      name: 'CSV load',
      dataConnectionId: 'dc-1',
      thingId: 'thing-1',
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
      thingId: 'thing-2',
      taskType: 'Rating curve',
      noWorkWarning: null,
    })
    expect(rows.monitoringTaskRows.value[0]).toMatchObject({
      id: 'mon-1',
      kind: 'monitoring',
      thingId: 'thing-3',
      statusName: 'Needs attention',
      statusSort: 'Needs attention',
      qualityRuleSummary: '2 RANGE CHECK, 1 SPIKE CHECK',
      qualityRuleCount: 3,
      qualityRuleBreakdown: [
        { label: 'RANGE CHECK', count: 2 },
        { label: 'SPIKE CHECK', count: 1 },
      ],
      monitoringRulesViolated: 2,
      noWorkWarning: null,
    })
  })

  it('builds rows from summary task responses without expanded related objects', () => {
    const rows = useOrchestrationTaskRows({
      activeTab: ref('ingestion'),
      workspaceTasks: ref([
        {
          id: 'etl-summary',
          name: 'Summary import',
          dataConnectionId: 'dc-summary',
          workspaceId: 'workspace-1',
          taskVariables: {},
          latestRun: null,
          schedule: null,
        },
      ] as any),
      dataProductTasks: ref([
        {
          id: 'dp-summary',
          name: 'Summary product',
          thingId: 'thing-summary',
          workspaceId: 'workspace-1',
          latestRun: null,
          schedule: null,
          aggregationTransformations: [{ id: 'agg-1' }],
          compositeExpressionTransformations: [],
          expressionTransformations: [],
          ratingCurveTransformations: [],
        },
      ] as any),
      monitoringTasks: ref([
        {
          id: 'mon-summary',
          name: 'Summary quality',
          thingId: 'thing-summary',
          workspaceId: 'workspace-1',
          latestRun: null,
          schedule: null,
          recipients: [],
          monitoredDatastreams: [
            {
              datastreamId: 'ds-1',
              rules: [{ ruleType: 'range' }, { ruleType: 'missing_data' }],
            },
          ],
        },
      ] as any),
      datastreamThingByDatastreamId: ref({}),
      runNowTriggeredByTaskId: {},
    })

    expect(rows.etlTaskRows.value[0]).toMatchObject({
      id: 'etl-summary',
      dataConnectionId: 'dc-summary',
      noWorkWarning: null,
    })
    expect(rows.dataProductTaskRows.value[0]).toMatchObject({
      id: 'dp-summary',
      thingId: 'thing-summary',
      taskType: 'Aggregation',
    })
    expect(rows.monitoringTaskRows.value[0]).toMatchObject({
      id: 'mon-summary',
      thingId: 'thing-summary',
      qualityRuleSummary: '1 Missing Data, 1 Range',
      qualityRuleCount: 2,
    })
  })

  it('flags tasks that have no configured work', () => {
    const rows = useOrchestrationTaskRows({
      activeTab: ref('ingestion'),
      workspaceTasks: ref([
        {
          id: 'etl-empty',
          name: 'Empty import',
          dataConnection: { id: 'dc-1' },
          latestRun: null,
          schedule: null,
          mappings: [],
        },
      ] as any),
      dataProductTasks: ref([
        {
          id: 'dp-empty',
          name: 'Empty product',
          thing: { id: 'thing-2' },
          latestRun: null,
          schedule: null,
          aggregationTransformations: [],
          compositeExpressionTransformations: [],
          expressionTransformations: [],
          ratingCurveTransformations: [],
        },
      ] as any),
      monitoringTasks: ref([
        {
          id: 'mon-empty',
          name: 'Empty quality task',
          thing: { id: 'thing-3' },
          latestRun: null,
          schedule: null,
          monitoredDatastreams: [{ rules: [] }],
        },
      ] as any),
      datastreamThingByDatastreamId: ref({}),
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

  it('displays inferred next run times for scheduled data product rows', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-13T12:00:00Z'))

    const rows = useOrchestrationTaskRows({
      activeTab: ref('aggregation'),
      workspaceTasks: ref([]),
      dataProductTasks: ref([
        {
          id: 'dp-interval',
          name: 'Scheduled rating curve',
          thing: { id: 'thing-2' },
          latestRun: null,
          schedule: {
            enabled: true,
            startTime: '2026-03-13T13:00:00Z',
            nextRunAt: null,
            crontab: null,
            interval: 1,
            intervalPeriod: 'days',
          },
          ratingCurveTransformations: [{}],
        },
      ] as any),
      monitoringTasks: ref([]),
      datastreamThingByDatastreamId: ref({}),
      runNowTriggeredByTaskId: {},
    })

    const row = rows.dataProductTaskRows.value[0]
    expect(row.nextRunAt).toBe('2026-03-14T13:00:00.000Z')
    expect(row.nextRun).not.toBe('-')

    vi.useRealTimers()
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
          thing: { id: 'thing-1' },
          latestRun: {
            id: 'run-ok',
            status: 'SUCCESS',
            result: { rulesViolated: 0 },
            startedAt: '2026-03-13T12:00:00Z',
          },
          schedule: null,
          monitoredDatastreams: [],
        },
      ] as any),
      datastreamThingByDatastreamId: ref({}),
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
          { name: 'Derived flow', taskType: 'Derivation' } as any,
        ])
        .map((row) => row.taskType)
    ).toEqual(['Aggregation', 'Derivation', 'Rating curve'])
  })
})
