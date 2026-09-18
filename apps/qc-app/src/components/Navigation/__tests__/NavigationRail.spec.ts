import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
import { VLayout } from 'vuetify/components'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const {
  qcDatastream,
  qcDatastreamId,
  resetState,
  clearEditTarget,
  currentView,
  selectedDrawer,
  isDrawerOpen,
  resumeDatastreamId,
  hasUnsavedChanges,
  push,
  assign,
  showView,
} = vi.hoisted(() => {
  const { ref: r, computed: c } = require('vue') as typeof import('vue')
  const qcDatastreamId = r<string | null>(null)
  const currentView = r('Edit')
  const selectedDrawer = r('Edit')
  const isDrawerOpen = r(true)
  return {
    qcDatastreamId,
    qcDatastream: c(() =>
      qcDatastreamId.value ? { id: qcDatastreamId.value } : null
    ),
    resetState: vi.fn(() => {
      qcDatastreamId.value = null
    }),
    clearEditTarget: vi.fn(async () => {
      qcDatastreamId.value = null
    }),
    currentView,
    selectedDrawer,
    isDrawerOpen,
    resumeDatastreamId: r<string | null>(null),
    hasUnsavedChanges: r(false),
    push: vi.fn(async () => {}),
    assign: vi.fn(),
    showView: vi.fn((view: string) => {
      currentView.value = view
      selectedDrawer.value = view
      isDrawerOpen.value = true
    }),
  }
})

vi.mock('@/store/dataVisualization', async () => {
  const { defineStore } = await import('pinia')
  return {
    useDataVisStore: defineStore('dataVisualization', () => ({
      qcDatastream,
      qcDatastreamId,
      resetState,
      setEditTarget: vi.fn(),
      clearEditTarget,
    })),
  }
})

vi.mock('@/store/userInterface', async () => {
  const { defineStore } = await import('pinia')
  return {
    DrawerType: { Edit: 'Edit', Select: 'Select', None: '' },
    useUIStore: defineStore('userInterface', () => ({
      currentView,
      selectedDrawer,
      isDrawerOpen,
      showView,
      onRailItemClicked: vi.fn((title: string) => {
        if (selectedDrawer.value === title) {
          isDrawerOpen.value = !isDrawerOpen.value
        } else showView(title)
      }),
    })),
  }
})

vi.mock('@/store/qcSession', async () => {
  const { defineStore } = await import('pinia')
  const { ref } = await import('vue')
  return {
    useQcSessionStore: defineStore('qcSession', () => ({
      resumeDatastreamId,
      inProgressSession: ref(null),
    })),
  }
})

vi.mock('@/store/hydroserver', async () => {
  const { defineStore } = await import('pinia')
  const { ref } = await import('vue')
  return {
    useHydroServer: defineStore('hydroserver', () => ({ hs: ref({}) })),
  }
})

vi.mock('@/store/workspaces', async () => {
  const { defineStore } = await import('pinia')
  const { ref } = await import('vue')
  return {
    useWorkspaceStore: defineStore('workspaces', () => ({
      selectedWorkspace: ref(null),
      clearSelection: vi.fn(),
    })),
  }
})

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ redraw: vi.fn() }),
}))

vi.mock('@/composables/useEditSession', async () => {
  const { ref } = await import('vue')
  return {
    ResumeSupersededError: class extends Error {},
    useEditSession: () => ({
      hasUnsavedChanges,
      unsavedEditCount: ref(0),
      saveDraft: vi.fn(),
      discardUnsavedEdits: vi.fn(),
      beginEditing: vi.fn(),
      startSession: vi.fn(),
      needsSession: ref(false),
      needsHistory: ref(false),
    }),
  }
})

vi.mock('@/router/router', () => ({ default: { push } }))

vi.mock('@uwrl/qc-utils', () => ({
  Snackbar: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

vi.mock('@/components/Navigation/SelectDrawer.vue', () => ({
  default: { name: 'SelectDrawer', render: () => null },
}))
vi.mock('@/components/Navigation/PerformanceCalibration.vue', () => ({
  default: { name: 'PerformanceCalibration', render: () => null },
}))

import NavigationRail from '@/components/Navigation/NavigationRail.vue'

function mountRail() {
  return mount(
    { render: () => h(VLayout, () => [h(NavigationRail)]) },
    {
      global: {
        plugins: [createTestPinia(), createTestVuetify()],
        stubs: {
          VTooltip: defineComponent({
            setup: (_, { slots }) => () => slots.activator?.({ props: {} }),
          }),
          VDialog: true,
        },
      },
    }
  )
}

describe('NavigationRail view switching', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    qcDatastreamId.value = 'm-1'
    resumeDatastreamId.value = 'm-1'
    currentView.value = 'Edit'
    selectedDrawer.value = 'Edit'
    hasUnsavedChanges.value = true
  })

  it('Select keeps the session, even with unsaved edits', async () => {
    const wrapper = mountRail()
    await wrapper.find('[data-testid="nav-rail-item-select"]').trigger('click')
    await flushPromises()

    expect(currentView.value).toBe('Select')
    expect(qcDatastreamId.value).toBe('m-1')
    expect(resumeDatastreamId.value).toBe('m-1')
    expect(clearEditTarget).not.toHaveBeenCalled()
    expect(wrapper.find('.v-dialog').exists()).toBe(false)
    wrapper.unmount()
  })

  it('Edit returns to the editor from the Select view', async () => {
    currentView.value = 'Select'
    selectedDrawer.value = 'Select'
    const wrapper = mountRail()
    const editRail = wrapper.find('[data-testid="nav-rail-item-edit"]')
    expect(editRail.attributes('aria-disabled')).toBe('false')
    await editRail.trigger('click')
    await flushPromises()

    expect(currentView.value).toBe('Edit')
    expect(qcDatastreamId.value).toBe('m-1')
    wrapper.unmount()
  })

  it('Edit stays disabled with no edit target', async () => {
    qcDatastreamId.value = null
    currentView.value = 'Select'
    selectedDrawer.value = 'Select'
    const wrapper = mountRail()
    const editRail = wrapper.find('[data-testid="nav-rail-item-edit"]')
    expect(editRail.attributes('aria-disabled')).toBe('true')
    await editRail.trigger('click')
    await flushPromises()

    expect(currentView.value).toBe('Select')
    wrapper.unmount()
  })
})

describe('NavigationRail leaving the editor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    qcDatastreamId.value = 'm-1'
    resumeDatastreamId.value = 'm-1'
    currentView.value = 'Edit'
    selectedDrawer.value = 'Edit'
    hasUnsavedChanges.value = false
    vi.stubGlobal('location', { ...window.location, assign })
  })

  it('Home clears the resume pointer before reloading', async () => {
    const wrapper = mountRail()
    await wrapper.find('button[aria-label="Home"]').trigger('click')
    await flushPromises()

    expect(resumeDatastreamId.value).toBeNull()
    expect(qcDatastreamId.value).toBeNull()
    expect(currentView.value).toBe('Select')
    expect(assign).toHaveBeenCalledWith('/')
    wrapper.unmount()
  })

  it('switching workspace navigates first, then clears the resume pointer', async () => {
    let pointerAtPush: string | null = null
    push.mockImplementationOnce(async () => {
      pointerAtPush = resumeDatastreamId.value
    })
    const wrapper = mountRail()
    await wrapper.find('[data-testid="nav-rail-workspaces"]').trigger('click')
    await flushPromises()

    expect(push).toHaveBeenCalledWith({
      name: 'Workspaces',
      query: { switch: '1' },
    })
    expect(pointerAtPush).toBe('m-1')
    expect(resumeDatastreamId.value).toBeNull()
    expect(clearEditTarget).toHaveBeenCalled()
    expect(currentView.value).toBe('Select')
    wrapper.unmount()
  })

  it('asks before leaving with unsaved edits', async () => {
    hasUnsavedChanges.value = true
    const wrapper = mountRail()
    await wrapper.find('[data-testid="nav-rail-workspaces"]').trigger('click')
    await flushPromises()

    expect(push).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBe('m-1')
    wrapper.unmount()
  })
})
