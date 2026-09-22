import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const { qcDatastream, inProgressSession, viewedSession, unsavedEditCount, openEditor } =
  vi.hoisted(() => {
    const { ref: r } = require('vue') as typeof import('vue')
    return {
      qcDatastream: r<{ id: string; name: string } | null>(null),
      inProgressSession: r<Record<string, string> | null>(null),
      viewedSession: r<Record<string, string> | null>(null),
      unsavedEditCount: r(0),
      openEditor: vi.fn(),
    }
  })

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ qcDatastream }),
}))

vi.mock('@/store/qcSession', () => ({
  useQcSessionStore: () => ({ inProgressSession, viewedSession }),
}))

vi.mock('@/composables/useEditSession', () => ({
  useEditSession: () => ({ unsavedEditCount }),
}))

vi.mock('@/composables/useEditEntry', () => ({
  useEditEntry: () => ({ openEditor }),
}))

import EditTargetPanel from '@/components/EditData/EditTargetPanel.vue'
import { formatDateRange } from '@/utils/time'

const mountPanel = () =>
  mount(EditTargetPanel, {
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })

beforeEach(() => {
  vi.clearAllMocks()
  qcDatastream.value = { id: 'mgd-1', name: 'Managed Temperature' }
  inProgressSession.value = {
    phenomenonTimeStart: '2025-01-05T00:00:00Z',
    phenomenonTimeEnd: '2025-02-01T00:00:00Z',
  }
  viewedSession.value = null
  unsavedEditCount.value = 0
})

describe('EditTargetPanel', () => {
  it('names what is being edited and the session window', () => {
    const text = mountPanel().text()
    expect(text).toContain('Managed Temperature')
    expect(text).toContain(
      formatDateRange('2025-01-05T00:00:00Z', '2025-02-01T00:00:00Z')
    )
  })

  it('reports unsaved edits, and says so when there are none', async () => {
    expect(mountPanel().text()).toContain('All edits saved')
    unsavedEditCount.value = 3
    expect(mountPanel().text()).toContain('3 unsaved edits')
    unsavedEditCount.value = 1
    expect(mountPanel().text()).toContain('1 unsaved edit')
  })

  it('shows the window of the session being viewed over the live one', () => {
    viewedSession.value = {
      phenomenonTimeStart: '2024-03-01T00:00:00Z',
      phenomenonTimeEnd: '2024-04-01T00:00:00Z',
    }
    expect(mountPanel().text()).toContain(
      formatDateRange('2024-03-01T00:00:00Z', '2024-04-01T00:00:00Z')
    )
  })

  it('goes back to the editor without touching the session', async () => {
    const wrapper = mountPanel()
    await wrapper.find('[data-testid="open-editor-btn"]').trigger('click')
    expect(openEditor).toHaveBeenCalledTimes(1)
  })

  it('renders nothing without an edit target', () => {
    qcDatastream.value = null
    expect(mountPanel().find('[data-testid="edit-target-panel"]').exists()).toBe(
      false
    )
  })
})
