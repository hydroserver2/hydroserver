import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { useOrchestrationTaskRows } from '../orchestration/useOrchestrationTaskRows'

describe('useOrchestrationTaskRows', () => {
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
    })
    expect(rows.monitoringTaskRows.value[0]).toMatchObject({
      id: 'mon-1',
      kind: 'monitoring',
      thingId: 'thing-3',
      qualityRuleSummary: '2 RANGE CHECK, 1 SPIKE CHECK',
      monitoringRulesViolated: 2,
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
      rows.sortRows([
        { name: 'Mean stage', taskType: 'Aggregation' } as any,
        { name: 'Curve output', taskType: 'Rating curve' } as any,
        { name: 'Derived flow', taskType: 'Derivation' } as any,
      ]).map((row) => row.taskType)
    ).toEqual(['Aggregation', 'Derivation', 'Rating curve'])
  })
})
