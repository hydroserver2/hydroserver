import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { useOrchestrationStore } from '../orchestration'
import { useWorkspaceStore } from '../workspaces'

describe('orchestration store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('derives linked datastream ids from lean task target identifiers', async () => {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = {
      id: 'workspace-1',
      name: 'Workspace 1',
      isPrivate: false,
    } as any

    const orchestrationStore = useOrchestrationStore()
    orchestrationStore.workspaceTasks = [
      {
        id: 'task-1',
        targetIdentifiers: ['ds-1', 'ds-2'],
        mappings: [],
      },
      {
        id: 'task-2',
        targetIdentifiers: [],
        mappings: [
          {
            sourceIdentifier: 'source-1',
            paths: [{ targetIdentifier: 'ds-3', dataTransformations: [] }],
          },
        ],
      },
      {
        id: 'task-3',
        targetIdentifiers: ['ds-1'],
        mappings: [],
      },
    ] as any
    orchestrationStore.workspaceDatastreams = [
      { id: 'ds-1', name: 'Datastream 1' },
      { id: 'ds-2', name: 'Datastream 2' },
      { id: 'ds-3', name: 'Datastream 3' },
      { id: 'ds-4', name: 'Datastream 4' },
    ] as any

    await nextTick()

    expect([...orchestrationStore.linkedDatastreamIds]).toEqual([
      'ds-1',
      'ds-2',
      'ds-3',
    ])
    expect(orchestrationStore.linkedDatastreams.map((d) => d.id)).toEqual([
      'ds-1',
      'ds-2',
      'ds-3',
    ])
  })
})
