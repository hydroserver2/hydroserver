import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// jsdom has no visualViewport; Vuetify's overlay positioning reads it.
;(globalThis as any).visualViewport ||= {
  addEventListener() {},
  removeEventListener() {},
  offsetLeft: 0,
  offsetTop: 0,
  width: 1024,
  height: 768,
  scale: 1,
}

const {
  leavePrompt,
  leaveWork,
  cancelLeave,
  keepSession,
  closeSession,
  saveAndLeave,
  discardEditsAndLeave,
  discardSessionAndLeave,
} = vi.hoisted(() => {
  const { ref: r } = require('vue') as typeof import('vue')
  return {
    leavePrompt: r<Record<string, unknown> | null>(null),
    leaveWork: r<string | null>(null),
    cancelLeave: vi.fn(),
    keepSession: vi.fn(),
    closeSession: vi.fn(),
    saveAndLeave: vi.fn(),
    discardEditsAndLeave: vi.fn(),
    discardSessionAndLeave: vi.fn(),
  }
})

vi.mock('@/composables/useLeaveSession', () => ({
  useLeaveSession: () => ({
    leavePrompt,
    leaveWork,
    cancelLeave,
    keepSession,
    closeSession,
    saveAndLeave,
    discardEditsAndLeave,
    discardSessionAndLeave,
  }),
}))

import LeaveSessionDialog from '@/components/EditData/LeaveSessionDialog.vue'

const mountDialog = () =>
  mount(LeaveSessionDialog, {
    attachTo: document.body,
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })

const dialogText = () =>
  document.querySelector('[data-testid="leave-session-dialog"]')?.textContent ??
  ''

const button = (testId: string) =>
  document.querySelector<HTMLElement>(`[data-testid="${testId}"]`)

beforeEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
  leavePrompt.value = null
  leaveWork.value = null
})

describe('LeaveSessionDialog', () => {
  it('shows nothing while no exit is pending', () => {
    mountDialog()
    expect(button('leave-session-dialog')).toBeNull()
  })

  it('offers save, discard and cancel for unsaved edits', async () => {
    leavePrompt.value = {
      datastreamName: 'Temp (QC)',
      kind: 'unsaved',
      unsavedCount: 2,
      canSave: true,
    }
    const wrapper = mountDialog()
    await wrapper.vm.$nextTick()

    const text = dialogText()
    expect(text).toContain('2 edits')
    expect(text).toContain('Resume it')
    expect(button('leave-save-btn')).not.toBeNull()
    expect(button('leave-save-btn')?.getAttribute('disabled')).toBeNull()
    expect(button('leave-discard-edits-btn')).not.toBeNull()

    button('leave-discard-edits-btn')?.click()
    expect(discardEditsAndLeave).toHaveBeenCalled()
    button('leave-save-btn')?.click()
    expect(saveAndLeave).toHaveBeenCalled()
    button('leave-cancel-btn')?.click()
    expect(cancelLeave).toHaveBeenCalled()
  })

  it('disables saving when no session is open', async () => {
    leavePrompt.value = {
      datastreamName: 'Temp (QC)',
      kind: 'unsaved',
      unsavedCount: 1,
      canSave: false,
    }
    const wrapper = mountDialog()
    await wrapper.vm.$nextTick()

    expect(button('leave-save-btn')?.getAttribute('disabled')).not.toBeNull()
    expect(dialogText()).toContain('No session is open')
  })

  it('offers keep or discard for a session with no edits', async () => {
    leavePrompt.value = {
      datastreamName: 'Temp (QC)',
      kind: 'empty',
      unsavedCount: 0,
      canSave: true,
    }
    const wrapper = mountDialog()
    await wrapper.vm.$nextTick()

    expect(dialogText()).toContain('Your session on Temp (QC) has no edits')
    expect(button('leave-save-btn')).toBeNull()

    button('leave-keep-btn')?.click()
    expect(keepSession).toHaveBeenCalled()
    button('leave-discard-session-btn')?.click()
    expect(discardSessionAndLeave).toHaveBeenCalled()
  })

  it('says the session stays in progress when everything is saved', async () => {
    leavePrompt.value = {
      datastreamName: 'Temp (QC)',
      kind: 'saved',
      unsavedCount: 0,
      canSave: true,
    }
    const wrapper = mountDialog()
    await wrapper.vm.$nextTick()

    expect(dialogText()).toContain('stays in progress')
    expect(button('leave-discard-session-btn')).toBeNull()

    button('leave-close-btn')?.click()
    expect(closeSession).toHaveBeenCalled()
  })

  it('locks the choices while one is running', async () => {
    leavePrompt.value = {
      datastreamName: 'Temp (QC)',
      kind: 'unsaved',
      unsavedCount: 1,
      canSave: true,
    }
    leaveWork.value = 'save'
    const wrapper = mountDialog()
    await wrapper.vm.$nextTick()

    expect(button('leave-cancel-btn')?.getAttribute('disabled')).not.toBeNull()
    expect(
      button('leave-discard-edits-btn')?.getAttribute('disabled')
    ).not.toBeNull()
  })
})
