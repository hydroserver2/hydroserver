import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, afterEach } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import StartEditingDialog from '@/components/EditData/StartEditingDialog.vue'
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

// The delete confirmation is a v-dialog, whose content Vuetify teleports
// out of the wrapper, so it is queried through the document instead.
const mountDialog = (props: Record<string, unknown> = {}) =>
  mount(StartEditingDialog, {
    props: { source, options, ...props },
    global: { plugins: [createTestVuetify()] },
    attachTo: document.body,
  })

const inDialog = (testId: string) =>
  document.querySelector(`[data-testid="${testId}"]`)

const clickInDialog = async (testId: string) => {
  const el = inDialog(testId)
  if (!el) throw new Error(`${testId} is not in the dialog`)
  ;(el as HTMLElement).click()
  await flushPromises()
}

afterEach(() => {
  document.body.innerHTML = ''
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

  it('heads the timeline with the start-a-session node, above the sessions', () => {
    const w = mountDialog()
    const ids = w
      .findAll('.v-timeline-item')
      .map((el) => el.attributes('data-testid') ?? 'new-session-node')
    // mgd-1 has an in-progress session, so only mgd-2 offers the node.
    expect(w.find('[data-testid="edit-managed-mgd-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="edit-managed-mgd-2"]').text()).toContain(
      'Start new session'
    )
    // mgd-1's sessions run oldest first; mgd-2's action node follows them.
    expect(ids).toEqual([
      'chooser-session-s-0',
      'chooser-session-s-1',
      'new-session-node',
    ])
  })

  it('renders sessions as a timeline, marked by status', () => {
    const w = mountDialog()
    const item = (id: string) => w.find(`[data-testid="chooser-session-${id}"]`)

    expect(w.findAll('.v-timeline-item[data-testid^="chooser-session-"]'))
      .toHaveLength(2)
    expect(item('s-1').classes()).toContain('qc-timeline__item--active')
    expect(item('s-1').find('.mdi-pencil').exists()).toBe(true)
    expect(item('s-0').classes()).toContain('qc-timeline__item--done')
    expect(item('s-0').find('.mdi-check').exists()).toBe(true)
  })

  it('offers delete on every session, and Continue only in progress', () => {
    const w = mountDialog()
    expect(w.find('[data-testid="delete-session-s-1"]').exists()).toBe(true)
    // Committed sessions are deletable now that the API allows it.
    expect(w.find('[data-testid="delete-session-s-0"]').exists()).toBe(true)
    expect(w.find('[data-testid="continue-session-s-0"]').exists()).toBe(false)
  })

  it('asks for confirmation, then emits deleteSession for that session', async () => {
    const w = mountDialog()
    await w.find('[data-testid="delete-session-s-1"]').trigger('click')
    expect(inDialog('confirm-delete-session-s-1')).not.toBeNull()
    await clickInDialog('confirm-delete-session-s-1')
    const [option, sessionId] = w.emitted('deleteSession')![0]
    expect(option).toMatchObject({ historyId: 'h-1' })
    expect(sessionId).toBe('s-1')
  })

  it('cancelling the confirmation emits nothing', async () => {
    const w = mountDialog()
    await w.find('[data-testid="delete-session-s-1"]').trigger('click')
    await clickInDialog('cancel-delete-session')
    expect(w.emitted('deleteSession')).toBeUndefined()
  })

  it('warns that a lone delete cannot be undone', async () => {
    const w = mountDialog()
    await w.find('[data-testid="delete-session-s-1"]').trigger('click')
    const dialog = inDialog('delete-session-dialog')!
    expect(dialog.textContent).toContain('cannot be undone')
    // One session, so it lists only that one and needs no extra tick-box.
    expect(
      document.querySelectorAll('[data-testid^="delete-chain-item-"]')
    ).toHaveLength(1)
    expect(inDialog('delete-session-acknowledge')).toBeNull()
    // The listing can be incomplete, so the warning stands on its own.
    expect(inDialog('delete-session-dependents-note')!.textContent).toContain(
      'deleted with it'
    )
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

describe('StartEditingDialog cascade delete', () => {
  // s-0 committed, s-1 built on it, s-2 built on s-1.
  const chained = [
    {
      historyId: 'h-1',
      managed: { id: 'mgd-1', name: 'Temp (QC)' },
      sessions: [
        {
          id: 's-0',
          status: 'committed',
          createdAt: '2024-12-01T09:00:00Z',
          description: 'First pass',
          phenomenonTimeStart: '2024-12-01T00:00:00Z',
          phenomenonTimeEnd: '2024-12-31T00:00:00Z',
          dependencyIds: [],
        },
        {
          id: 's-1',
          status: 'committed',
          createdAt: '2025-01-05T09:00:00Z',
          description: 'Second pass',
          phenomenonTimeStart: '2025-01-05T00:00:00Z',
          phenomenonTimeEnd: '2025-01-15T00:00:00Z',
          dependencyIds: ['s-0'],
        },
        {
          id: 's-2',
          status: 'in_progress',
          createdAt: '2025-02-01T09:00:00Z',
          description: 'Third pass',
          phenomenonTimeStart: '2025-02-01T00:00:00Z',
          phenomenonTimeEnd: '2025-02-10T00:00:00Z',
          dependencyIds: ['s-1'],
        },
      ],
    },
  ] as any

  const mountChained = () =>
    mount(StartEditingDialog, {
      props: { source, options: chained },
      global: { plugins: [createTestVuetify()] },
      attachTo: document.body,
    })

  const openDeleteFor = async (id: string) => {
    const w = mountChained()
    await w.find(`[data-testid="delete-session-${id}"]`).trigger('click')
    return w
  }

  it('lists the whole chain, target last, when deleting the root', async () => {
    await openDeleteFor('s-0')
    const ids = [
      ...document.querySelectorAll('[data-testid^="delete-chain-item-"]'),
    ].map((el) => el.getAttribute('data-testid'))
    expect(ids).toEqual([
      'delete-chain-item-s-2',
      'delete-chain-item-s-1',
      'delete-chain-item-s-0',
    ])
  })

  it('says how many sessions go and names them', async () => {
    await openDeleteFor('s-0')
    const dialog = inDialog('delete-session-dialog')!
    expect(dialog.textContent).toContain('Delete 3 sessions?')
    expect(dialog.textContent).toContain('First pass')
    expect(dialog.textContent).toContain('Second pass')
    expect(dialog.textContent).toContain('Third pass')
    expect(dialog.textContent).toContain('cannot be undone')
  })

  it('marks which session the user actually picked', async () => {
    await openDeleteFor('s-0')
    const target = inDialog('delete-chain-item-s-0')!
    expect(target.textContent).toContain('the one you picked')
    expect(inDialog('delete-chain-item-s-1')!.textContent).not.toContain(
      'the one you picked'
    )
  })

  it('holds the delete until the cascade is acknowledged', async () => {
    const w = await openDeleteFor('s-0')
    const confirm = inDialog('confirm-delete-session-s-0') as HTMLButtonElement
    expect(confirm.disabled).toBe(true)

    confirm.click()
    await flushPromises()
    expect(w.emitted('deleteSession')).toBeUndefined()

    // v-checkbox puts the test id on its wrapper; the input carries the model.
    const box = document.querySelector(
      '[data-testid="delete-session-acknowledge"] input'
    ) as HTMLInputElement
    box.click()
    await flushPromises()
    expect(
      (inDialog('confirm-delete-session-s-0') as HTMLButtonElement).disabled
    ).toBe(false)
    await clickInDialog('confirm-delete-session-s-0')
    expect(w.emitted('deleteSession')![0][1]).toBe('s-0')
  })

  it('needs no acknowledgement for a leaf session', async () => {
    await openDeleteFor('s-2')
    expect(inDialog('delete-session-acknowledge')).toBeNull()
    expect(
      (inDialog('confirm-delete-session-s-2') as HTMLButtonElement).disabled
    ).toBe(false)
  })

  it('tells the user on the row how far the delete reaches', async () => {
    const w = mountChained()
    expect(
      w.find('[data-testid="delete-session-s-0"]').attributes('title')
    ).toBe('Delete this session and the 2 built on it')
    expect(
      w.find('[data-testid="delete-session-s-2"]').attributes('title')
    ).toBe('Delete this session')
  })
})
