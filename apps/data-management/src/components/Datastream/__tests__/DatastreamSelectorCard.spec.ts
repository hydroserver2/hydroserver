import { nextTick } from 'vue'
import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useOrchestrationStore } from '@/store/orchestration'
import DatastreamSelectorCard from '../DatastreamSelectorCard.vue'

describe('DatastreamSelectorCard linked destinations', () => {
  const slotStub = { template: '<div><slot /></div>' }
  const stubs = {
    VCard: slotStub,
    VCardText: slotStub,
    VDialog: slotStub,
    'v-btn-cancel': slotStub,
    'v-btn-icon': slotStub,
  }

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('hides linked rows until requested, redlines them, and blocks selection', async () => {
    const linkedDatastream = { id: 'linked', name: 'Linked datastream' }
    const availableDatastream = {
      id: 'available',
      name: 'Available datastream',
    }
    const orchestrationStore = useOrchestrationStore()
    orchestrationStore.workspaceTasks = [
      {
        id: 'task-1',
        mappings: [
          {
            sourceIdentifier: 'source',
            targetDatastream: linkedDatastream,
          },
        ],
      },
    ] as any

    const wrapper = shallowMount(DatastreamSelectorCard, {
      props: {
        cardTitle: 'Select output datastream',
        datastreams: [linkedDatastream, availableDatastream] as any,
        enforceUniqueSelections: true,
      },
      global: {
        stubs,
      },
    })
    const component = wrapper.vm as any

    expect(component.visibleDatastreams.map((item: any) => item.id)).toEqual([
      'available',
    ])

    component.showLinkedDatastreams = true
    await nextTick()

    expect(component.visibleDatastreams.map((item: any) => item.id)).toEqual([
      'available',
      'linked',
    ])
    expect(wrapper.find('.datastream-selector-row--linked').exists()).toBe(true)

    component.onDatastreamClick(linkedDatastream)
    await nextTick()

    expect(component.openLinkConflictModal).toBe(true)
    expect(wrapper.emitted('selectedDatastream')).toBeUndefined()
    expect(wrapper.text()).toContain("this action can't be completed")
  })

  it('keeps linked datastreams selectable when the field is an input', async () => {
    const linkedDatastream = { id: 'linked', name: 'Linked datastream' }
    useOrchestrationStore().workspaceTasks = [
      {
        id: 'task-1',
        mappings: [
          {
            sourceIdentifier: 'source',
            targetDatastream: linkedDatastream,
          },
        ],
      },
    ] as any

    const wrapper = shallowMount(DatastreamSelectorCard, {
      props: {
        cardTitle: 'Select input datastream',
        datastreams: [linkedDatastream] as any,
      },
      global: { stubs },
    })
    const component = wrapper.vm as any

    expect(component.visibleDatastreams).toHaveLength(1)
    expect(wrapper.find('.datastream-selector-row--linked').exists()).toBe(
      false
    )

    component.onDatastreamClick(linkedDatastream)
    await nextTick()

    expect(wrapper.emitted('selectedDatastream')?.[0]).toEqual([
      linkedDatastream,
    ])
    expect(component.openLinkConflictModal).toBe(false)
  })
})
