import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import cases from '../../../../../django/contracts/merge-patch-cases.json'

const jsonResponse = (data: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  })

describe('TaskService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it.each(cases.filter(({ patch }) => Object.keys(patch).length > 0))(
    'sends a merge patch: $name',
    async ({ original: fields, updated: changes, patch }) => {
      const original = { id: 'task-1', ...fields }
      const updated = { id: 'task-1', ...changes }
      const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({ data: updated }))
      vi.stubGlobal('fetch', fetchMock)

      const client = new HydroServer({ host: 'https://hydro.example.com' })
      const response = await client.tasks.update(updated, original)

      expect(fetchMock.mock.calls[0][0]).toBe(
        'https://hydro.example.com/api/ogc/collections/etl-tasks/items/task-1'
      )
      expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
      expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(patch)
      expect(fetchMock.mock.calls[0][1].headers.get('Content-Type')).toBe(
        'application/merge-patch+json'
      )
      expect(response.ok).toBe(true)
    }
  )

  it.each([
    { taskVariables: { station: 'A', parameter: 'temperature' } },
    {},
  ])('omits unchanged or unsupplied taskVariables: %j', async (variables) => {
    const original = {
      id: 'task-1',
      name: 'Original task',
      taskVariables: { station: 'A', parameter: 'temperature' },
    }
    const updated = { id: original.id, name: 'Updated task', ...variables }
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({ data: updated }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.tasks.update(updated, original)

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ name: 'Updated task' })
  })

  it('skips the PATCH request when taskVariables are unchanged', async () => {
    const original = {
      id: 'task-1',
      taskVariables: { station: 'A', parameter: 'temperature' },
    }
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({ data: original }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.tasks.update({ ...original, taskVariables: { ...original.taskVariables } }, original)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][1].method).toBe('GET')
  })

  it('unwraps the item envelope from triggered and fetched runs', async () => {
    const envelope = {
      data: { id: 'run-1', status: 'PENDING' },
      included: null,
      links: [
        {
          href: 'https://hydro.example.com/api/ogc/collections/etl-tasks/items/task-1/runs/run-1',
          rel: 'self',
          type: 'application/json',
        },
      ],
    }
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => jsonResponse(envelope)))

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const triggered = await client.tasks.runTask('task-1')
    const fetched = await client.tasks.getTaskRun('task-1', 'run-1')

    expect(triggered.ok && triggered.data).toEqual({ id: 'run-1', status: 'PENDING' })
    expect(fetched.ok && fetched.data).toEqual({ id: 'run-1', status: 'PENDING' })
  })

  it('forwards task run payloads without normalization', async () => {
    const rawResult = {
      message: 'Loaded 12 total observation(s) into 1 datastream(s).',
      runtime_variables: {
        extractor: {
          source_uri: 'https://example.com/runtime.csv',
        },
      },
      failure_count: 1,
      target_results: {
        'target-1': {
          status: 'failed',
          error: 'Unable to load target-1',
        },
      },
    }

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          data: [
            {
              id: 'run-1',
              status: 'SUCCESS',
              startedAt: '2026-03-12T12:00:00Z',
              finishedAt: '2026-03-12T12:05:00Z',
              result: rawResult,
            },
          ],
          meta: { offset: 0, limit: 200, numberMatched: 1 },
        })
      )
    )

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.tasks.getTaskRuns('task-1', {
      sortby: ['-startedAt'],
    })

    expect(response.ok).toBe(true)
    expect(response.data[0].result).toEqual(rawResult)
  })

  it('merges paginated results in page order when fetched concurrently', async () => {
    const pageData: Record<string, Array<{ id: string }>> = {
      '0': [{ id: 'a' }, { id: 'b' }],
      '2': [{ id: 'c' }, { id: 'd' }],
      '4': [{ id: 'e' }, { id: 'f' }],
      // A real server returns an empty page once past the true end of data -
      // this is what proves completion when numberMatched (6) happens to be an
      // exact multiple of limit, since a full last page alone can't tell the
      // client whether more data exists.
      '6': [],
    }

    const fetchMock = vi.fn((input: any) => {
      const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
      return Promise.resolve(
        jsonResponse({
          data: pageData[offset],
          meta: { offset: Number(offset), limit: 2, numberMatched: 6 },
        })
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const items = await client.tasks.listAllItems({ limit: 2 })

    expect(items.map((item: any) => item.id)).toEqual([
      'a',
      'b',
      'c',
      'd',
      'e',
      'f',
    ])
    // first page + two remaining pages implied by numberMatched + one
    // confirming fetch proving there's nothing past the (exact) total
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('omits empty ids from create payloads', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'monitoring-task-1',
        name: 'Range checks',
        description: null,
        recipients: [],
        monitoringSite: { id: 'monitoringSite-1', name: 'Site 1' },
        ruleTypeCounts: {},
        schedule: null,
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.monitoringTasks.create({
      id: '',
      name: 'Range checks',
      monitoringSiteId: 'monitoringSite-1',
      description: null,
      recipients: [],
      ruleTypeCounts: {},
      schedule: null,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/ogc/collections/monitoring-tasks/items'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Range checks',
      monitoringSiteId: 'monitoringSite-1',
      description: null,
      recipients: [],
      ruleTypeCounts: {},
      schedule: null,
    })
  })
})
