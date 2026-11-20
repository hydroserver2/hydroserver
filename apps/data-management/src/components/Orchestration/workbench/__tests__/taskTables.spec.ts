import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import IngestionTaskTable from '../IngestionTaskTable.vue'
import OrchestrationTaskTable from '../OrchestrationTaskTable.vue'

const task = {
  id: 'task-1',
  name: 'Example task',
  statusSort: 'OK',
  lastRun: 'Never',
  nextRun: 'Not scheduled',
  schedule: null,
}

describe('orchestration task tables', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('opens ingestion task details when the task name is clicked', async () => {
    const wrapper = shallowMount(IngestionTaskTable, {
      props: {
        tasks: [task] as any,
        statusFilter: [],
        canEdit: true,
        accent: '#000000',
      },
    })

    await wrapper.get('.ingestion-task-name').trigger('click')

    expect(wrapper.emitted('open-task')).toEqual([[task]])
  })

  it('opens aggregation and quality task details when the task name is clicked', async () => {
    const wrapper = shallowMount(OrchestrationTaskTable, {
      props: {
        tasks: [task] as any,
        statusFilter: [],
        taskTypeFilter: [],
        canEdit: true,
        accent: '#000000',
      },
    })

    await wrapper.get('.task-name').trigger('click')

    expect(wrapper.emitted('open-task')).toEqual([[task]])
  })
})
