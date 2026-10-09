import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const editLock = ref<'readOnly' | 'preview' | null>(null)
vi.mock('@/composables/useEditLock', () => ({
  useEditLock: () => ({ editLock }),
}))

const selectedOperation = ref<string | null>('changeValues')
const filterRangeActive = ref(false)
vi.mock('@/store/userInterface', () => ({
  useUIStore: () => ({ selectedOperation, filterRangeActive }),
}))

const selectedData = ref<number[] | null>([1, 2])
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ selectedData }),
}))

vi.mock('../operations', () => ({
  operationsById: {
    changeValues: {
      id: 'changeValues',
      title: 'Change values',
      description: '',
      icon: 'mdi-pencil',
      group: 'edit',
      requiresSelection: true,
      component: { template: '<div data-testid="op-body" />' },
    },
  },
}))

import OperationPanel from '@/components/EditData/OperationPanel.vue'

const mountPanel = () =>
  mount(OperationPanel, {
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })

beforeEach(() => {
  editLock.value = null
})

describe('OperationPanel edit lock', () => {
  it('renders the operation when unlocked', async () => {
    const w = mountPanel()
    await flushPromises()
    expect(w.find('[data-testid="op-body"]').exists()).toBe(true)
  })

  it('blocks the operation on a committed session', async () => {
    editLock.value = 'readOnly'
    const w = mountPanel()
    await flushPromises()
    expect(w.find('[data-testid="operation-read-only-blocked"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-body"]').exists()).toBe(false)
  })

  it('blocks the operation while previewing', async () => {
    editLock.value = 'preview'
    const w = mountPanel()
    await flushPromises()
    expect(w.find('[data-testid="operation-preview-blocked"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-body"]').exists()).toBe(false)
  })
})
