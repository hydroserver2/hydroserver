import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { Task } from '../Models/task.model'

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

  it('adds and removes mapping targets', () => {
    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const task = new Task({
      mappings: [
        {
          sourceIdentifier: 'source-1',
          paths: [
            { targetIdentifier: 'target-1', dataTransformations: [] },
            { targetIdentifier: 'target-2', dataTransformations: [] },
          ],
        },
      ],
    })

    client.tasks.addMapping(task)
    expect(task.mappings).toHaveLength(2)

    client.tasks.removeTarget(task, 'target-1')
    expect(task.mappings[0]?.paths).toEqual([
      { targetIdentifier: 'target-2', dataTransformations: [] },
    ])
  })
})
