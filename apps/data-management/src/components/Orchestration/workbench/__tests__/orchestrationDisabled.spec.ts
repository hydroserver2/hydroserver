import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import IngestionTaskTable from '../IngestionTaskTable.vue'
import OrchestrationTaskTable from '../OrchestrationTaskTable.vue'
import { ORCHESTRATION_DISABLED_TOOLTIP } from '@/composables/orchestration/orchestrationAvailability'

vi.mock(
  '@/composables/orchestration/orchestrationAvailability',
  async (importOriginal) => ({
    ...(await importOriginal<
      typeof import('@/composables/orchestration/orchestrationAvailability')
    >()),
    isOrchestrationEnabled: () => false,
  })
)

const task = {
  id: 'task-1',
  name: 'Example task',
  statusSort: 'OK',
  lastRun: 'Never',
  nextRun: 'Not scheduled',
  schedule: null,
}

// Render the tooltip's activator and content so both can be asserted on.
const global = {
  stubs: {
    VTooltip: {
      template: '<div><slot name="activator" :props="{}" /><slot /></div>',
    },
  },
}

describe('orchestration task tables with orchestration disabled', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows a disabled ingestion Run now button with the disabled tooltip', async () => {
    const wrapper = shallowMount(IngestionTaskTable, {
      props: {
        tasks: [task] as any,
        statusFilter: [],
        canEdit: true,
        accent: '#000000',
      },
      global,
    })

    const button = wrapper.get('[data-testid="run-now-disabled"]')
    expect(button.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain(ORCHESTRATION_DISABLED_TOOLTIP)

    await button.trigger('click')
    expect(wrapper.emitted('run-now')).toBeUndefined()
  })

  it('shows a disabled data product and quality Run now button with the disabled tooltip', async () => {
    const wrapper = shallowMount(OrchestrationTaskTable, {
      props: {
        tasks: [task] as any,
        statusFilter: [],
        taskTypeFilter: [],
        canEdit: true,
        accent: '#000000',
      },
      global,
    })

    const button = wrapper.get('[data-testid="run-now-disabled"]')
    expect(button.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain(ORCHESTRATION_DISABLED_TOOLTIP)

    await button.trigger('click')
    expect(wrapper.emitted('run-now')).toBeUndefined()
  })

  it('hides Run now for read-only users even when orchestration is disabled', () => {
    const wrapper = shallowMount(IngestionTaskTable, {
      props: {
        tasks: [task] as any,
        statusFilter: [],
        canEdit: false,
        accent: '#000000',
      },
      global,
    })

    expect(wrapper.find('[data-testid="run-now-disabled"]').exists()).toBe(
      false
    )
  })
})
