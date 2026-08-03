import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import StartEditingDialog from '@/components/EditData/StartEditingDialog.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const source = { id: 'src-1', name: 'Raw Temp' } as any

const options = [
  {
    historyId: 'h-1',
    managed: {
      id: 'mgd-1',
      name: 'Temp (QC)',
      valueCount: 1234,
      processingLevel: { definition: 'Quality Controlled' },
    },
    sessions: [
      {
        id: 's-1',
        status: 'in_progress',
        createdAt: '2025-01-05T09:00:00Z',
        phenomenonTimeStart: '2025-01-05T00:00:00Z',
        phenomenonTimeEnd: '2025-01-15T00:00:00Z',
        description: '',
      },
      {
        id: 's-0',
        status: 'committed',
        createdAt: '2024-12-01T09:00:00Z',
        description: 'Removed spikes',
        phenomenonTimeStart: '2024-12-01T00:00:00',
        phenomenonTimeEnd: '2024-12-31T00:00:00',
      },
    ],
  },
  { historyId: 'h-2', managed: { id: 'mgd-2', name: 'Temp (QC v2)' }, sessions: [] },
] as any

const mountDialog = (props: Record<string, unknown> = {}) =>
  mount(StartEditingDialog, {
    props: { source, options, ...props },
    global: { plugins: [createTestVuetify()] },
  })

describe('StartEditingDialog', () => {
  it('lists managed datastreams and labels in-progress vs committed sessions', () => {
    const w = mountDialog()
    expect(w.text()).toContain('Raw Temp')
    expect(w.text()).toContain('Temp (QC)')
    expect(w.text()).toContain('In progress')
    expect(w.text()).toContain('Committed')
  })

  it('offers Continue on the in-progress session row, not in the header', () => {
    const w = mountDialog()
    // mgd-1 has an in-progress session: continuing hangs off that row.
    expect(w.find('[data-testid="edit-managed-mgd-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="continue-session-s-1"]').text()).toContain(
      'Continue'
    )
    // mgd-2 has none, so the header offers starting one.
    expect(w.find('[data-testid="edit-managed-mgd-2"]').text()).toContain(
      'Start new'
    )
  })

  it('offers discard only on the in-progress session', () => {
    const w = mountDialog()
    expect(w.find('[data-testid="delete-session-s-1"]').exists()).toBe(true)
    expect(w.find('[data-testid="continue-session-s-0"]').exists()).toBe(false)
    expect(w.find('[data-testid="delete-session-s-0"]').exists()).toBe(false)
  })

  it('asks for confirmation, then emits deleteSession for that session', async () => {
    const w = mountDialog()
    await w.find('[data-testid="delete-session-s-1"]').trigger('click')
    const confirm = w.find('[data-testid="confirm-delete-session-s-1"]')
    expect(confirm.exists()).toBe(true)
    await confirm.trigger('click')
    const [option, sessionId] = w.emitted('deleteSession')![0]
    expect(option).toMatchObject({ historyId: 'h-1' })
    expect(sessionId).toBe('s-1')
  })

  it('cancelling the discard confirmation emits nothing', async () => {
    const w = mountDialog()
    await w.find('[data-testid="delete-session-s-1"]').trigger('click')
    await w.find('[data-testid="cancel-delete-session"]').trigger('click')
    expect(w.find('[data-testid="confirm-delete-session-s-1"]').exists()).toBe(
      false
    )
    expect(w.emitted('deleteSession')).toBeUndefined()
  })

  it('formats session date ranges readably', () => {
    const w = mountDialog()
    expect(w.text()).toContain('Dec 1 – Dec 31, 2024')
  })

  it('shows the period alongside the description on a described session', () => {
    const w = mountDialog()
    // s-0 is committed and described, so the description takes the title and
    // the window has to surface underneath it.
    expect(w.text()).toContain('Removed spikes')
    expect(w.text()).toContain('Dec 1 – Dec 31, 2024')
  })

  it('shows a recap line with processing level, observations, and sessions', () => {
    const w = mountDialog()
    expect(w.text()).toContain('Quality Controlled')
    expect(w.text()).toContain('1,234 obs')
    expect(w.text()).toContain('2 sessions, 1 in progress')
  })

  it('asks for confirmation, then emits delete with the chosen option', async () => {
    const w = mountDialog()
    await w.find('[data-testid="delete-managed-mgd-1"]').trigger('click')
    const confirm = w.find('[data-testid="confirm-delete-mgd-1"]')
    expect(confirm.exists()).toBe(true)
    await confirm.trigger('click')
    expect(w.emitted('delete')![0][0]).toMatchObject({ historyId: 'h-1' })
  })

  it('emits edit from the in-progress row and from the header', async () => {
    const w = mountDialog()
    await w.find('[data-testid="continue-session-s-1"]').trigger('click')
    expect(w.emitted('edit')![0][0]).toMatchObject({ historyId: 'h-1' })
    await w.find('[data-testid="edit-managed-mgd-2"]').trigger('click')
    expect(w.emitted('edit')![1][0]).toMatchObject({ historyId: 'h-2' })
  })

  it('emits create and cancel', async () => {
    const w = mountDialog()
    await w.find('[data-testid="chooser-create-managed"]').trigger('click')
    expect(w.emitted('create')).toHaveLength(1)
    await w.find('[data-testid="chooser-cancel"]').trigger('click')
    expect(w.emitted('cancel')).toHaveLength(1)
  })

  it('shows an empty hint with only the create option when there are no managed datastreams', () => {
    const w = mountDialog({ options: [] })
    expect(w.text()).toContain('No QC datastreams')
    expect(w.find('[data-testid="chooser-create-managed"]').exists()).toBe(true)
  })
})
