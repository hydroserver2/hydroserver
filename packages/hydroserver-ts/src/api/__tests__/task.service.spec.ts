import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

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
        jsonResponse(
          [
            {
              id: 'run-1',
              status: 'SUCCESS',
              startedAt: '2026-03-12T12:00:00Z',
              finishedAt: '2026-03-12T12:05:00Z',
              result: rawResult,
            },
          ],
          { 'X-Total-Pages': '1' }
        )
      )
    )

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.tasks.getTaskRuns('task-1', {
      order_by: ['-startedAt'],
    })

    expect(response.ok).toBe(true)
    expect(response.data[0].result).toEqual(rawResult)
  })

  it('merges paginated results in page order when fetched concurrently', async () => {
    const pageData: Record<string, Array<{ id: string }>> = {
      '1': [{ id: 'a' }, { id: 'b' }],
      '2': [{ id: 'c' }, { id: 'd' }],
      '3': [{ id: 'e' }, { id: 'f' }],
    }

    const fetchMock = vi.fn((input: any) => {
      const page = new URL(String(input)).searchParams.get('page') ?? '1'
      return Promise.resolve(
        jsonResponse(pageData[page], { 'X-Total-Pages': '3' })
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const items = await client.tasks.listAllItems()

    expect(items.map((item: any) => item.id)).toEqual([
      'a',
      'b',
      'c',
      'd',
      'e',
      'f',
    ])
    // first page + two remaining pages
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('omits empty ids from create payloads', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'monitoring-task-1',
        name: 'Range checks',
        description: null,
        recipients: [],
        thing: { id: 'thing-1', name: 'Site 1' },
        monitoredDatastreams: [],
        schedule: null,
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.monitoringTasks.create({
      id: '',
      name: 'Range checks',
      thingId: 'thing-1',
      description: null,
      recipients: [],
      schedule: null,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/monitoring/tasks'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Range checks',
      thingId: 'thing-1',
      description: null,
      recipients: [],
      schedule: null,
    })
  })
})
