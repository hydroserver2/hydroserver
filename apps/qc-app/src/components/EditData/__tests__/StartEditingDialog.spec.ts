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
        phenomenonTimeStart: '2025-01-05T00:00:00Z',
        phenomenonTimeEnd: '2025-01-15T00:00:00Z',
        description: '',
      },
      {
        id: 's-0',
        status: 'committed',
        phenomenonTimeStart: '2024-12-01T00:00:00Z',
        phenomenonTimeEnd: '2024-12-31T00:00:00Z',
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

  it('labels the action by whether an in-progress session exists', () => {
    const w = mountDialog()
    expect(w.find('[data-testid="edit-managed-mgd-1"]').text()).toContain(
      'Continue'
    )
    expect(w.find('[data-testid="edit-managed-mgd-2"]').text()).toContain(
      'Start new'
    )
  })

  it('formats session date ranges like the date inputs (MM/DD/YYYY HH:MM)', () => {
    const w = mountDialog()
    expect(w.text()).toMatch(
      /\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} to \d{2}\/\d{2}\/\d{4} \d{2}:\d{2}/
    )
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

  it('emits edit with the chosen option', async () => {
    const w = mountDialog()
    await w.find('[data-testid="edit-managed-mgd-1"]').trigger('click')
    expect(w.emitted('edit')![0][0]).toMatchObject({ historyId: 'h-1' })
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
