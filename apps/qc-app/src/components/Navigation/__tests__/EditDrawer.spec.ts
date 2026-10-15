import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const editLock = ref<'readOnly' | 'preview' | null>(null)
vi.mock('@/composables/useEditLock', () => ({
  useEditLock: () => ({ editLock }),
}))

const selectedOperation = ref<string | null>(null)
vi.mock('@/store/userInterface', () => ({
  useUIStore: () => ({ selectedOperation }),
}))

const selectedData = ref<number[] | null>([1])
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ selectedData }),
}))

vi.mock('@/components/EditData/operations', () => {
  const op = (id: string, group: string) => ({
    id,
    title: id,
    description: '',
    icon: 'mdi-x',
    group,
    requiresSelection: group === 'edit',
  })
  return {
    operationsByGroup: {
      filter: [op('valueThreshold', 'filter')],
      edit: [op('changeValues', 'edit')],
      add: [op('addPoints', 'add')],
    },
    colorForOperation: () => 'primary',
  }
})

import EditDrawer from '@/components/Navigation/EditDrawer.vue'

const mountDrawer = () =>
  mount(EditDrawer, {
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })

const isDisabled = (w: ReturnType<typeof mountDrawer>, id: string) =>
  w.find(`[data-testid="op-${id}"]`).classes().includes('v-list-item--disabled')

beforeEach(() => {
  editLock.value = null
  selectedOperation.value = null
})

describe('EditDrawer edit lock', () => {
  it('enables every operation when unlocked', async () => {
    const w = mountDrawer()
    await flushPromises()
    expect(w.find('[data-testid="edit-drawer-read-only"]').exists()).toBe(false)
    for (const id of ['valueThreshold', 'changeValues', 'addPoints']) {
      expect(isDisabled(w, id)).toBe(false)
    }
  })

  it('disables every operation and explains why on a committed session', async () => {
    editLock.value = 'readOnly'
    const w = mountDrawer()
    await flushPromises()
    expect(w.find('[data-testid="edit-drawer-read-only"]').exists()).toBe(true)
    for (const id of ['valueThreshold', 'changeValues', 'addPoints']) {
      expect(isDisabled(w, id)).toBe(true)
    }
  })
})
