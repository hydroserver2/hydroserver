import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import type { Pinia } from 'pinia'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
import { useHydroServer } from '@/store/hydroserver'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { useQcSessionStore } from '@/store/qcSession'
import { unwrap } from '@/services/qualityControl/unwrap'
import SessionList from '@/components/EditData/SessionList.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const win = (start: string, end: string) => ({
  phenomenonTimeStart: start,
  phenomenonTimeEnd: end,
})

let pinia: Pinia
let qc: ReturnType<typeof makeQcFake>

beforeEach(() => {
  pinia = createTestPinia()
  qc = makeQcFake()
  useHydroServer().hs = {
    qualityControlHistories: qc.histories,
    qualityControlSessions: qc.sessions,
    qualityControlOperations: qc.operations,
  } as any
})

const mountList = () =>
  mount(SessionList, {
    global: { plugins: [pinia, createTestVuetify()] },
    slots: { operations: '<div data-testid="ops-panel">ops</div>' },
  })

/** Seed a committed + an in-progress session and load them into the store. */
async function seedAndLoad() {
  const h = unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  )
  const committed = unwrap(
    await qc.sessions.create(h.id, win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'))
  )
  await qc.sessions.commit(h.id, committed.id)
  const inProgress = unwrap(
    await qc.sessions.create(h.id, win('2025-02-01T00:00:00Z', '2025-03-01T00:00:00Z'))
  )
  const store = useQcSessionStore()
  await store.loadSessions(h.id)
  return { store, committedId: committed.id, inProgressId: inProgress.id }
}

describe('SessionList', () => {
  it('renders an empty state when there are no sessions', () => {
    expect(mountList().text()).toContain('No sessions yet')
  })

  it('renders committed and in-progress sessions, marking the editable one', async () => {
    const { committedId, inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.find(`[data-testid="session-${committedId}"]`).exists()).toBe(true)
    expect(wrapper.find(`[data-testid="session-${inProgressId}"]`).exists()).toBe(true)
    expect(wrapper.text()).toContain('Editing')
  })

  it('marks each session with its status, not just the editable one', async () => {
    const { committedId, inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    const marker = (id: string) => wrapper.find(`[data-testid="session-${id}"]`)
    expect(marker(committedId).classes()).toContain('qc-timeline__item--done')
    expect(marker(committedId).find('.mdi-check').exists()).toBe(true)
    expect(marker(inProgressId).classes()).toContain(
      'qc-timeline__item--active'
    )
    expect(marker(inProgressId).find('.mdi-pencil').exists()).toBe(true)
  })

  it('lists sessions oldest first, so the most recent is at the bottom', async () => {
    const { committedId, inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    const ids = wrapper
      .findAll('.v-timeline-item[data-testid^="session-"]')
      .map((item) => item.attributes('data-testid'))
    expect(ids).toEqual([`session-${committedId}`, `session-${inProgressId}`])
  })

  it('orders by creation even when sessions share a phenomenon-time window', async () => {
    // Continuing work after a commit reuses the same window, so the windows
    // tie and only the creation time distinguishes the sessions.
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const sameWindow = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    const first = unwrap(await qc.sessions.create(h.id, sameWindow))
    await qc.sessions.commit(h.id, first.id)
    const second = unwrap(await qc.sessions.create(h.id, sameWindow))
    await useQcSessionStore().loadSessions(h.id)

    const wrapper = mountList()
    await flushPromises()
    const ids = wrapper
      .findAll('.v-timeline-item[data-testid^="session-"]')
      .map((item) => item.attributes('data-testid'))
    expect(ids).toEqual([`session-${first.id}`, `session-${second.id}`])
  })

  // Selecting a session reloads observations and replays operations, so the
  // list only reports the intent; the view owns the work.
  it('emits view for a committed session', async () => {
    const { committedId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    await wrapper.find(`[data-testid="session-header-${committedId}"]`).trigger('click')
    expect(wrapper.emitted('view')![0]).toEqual([committedId])
  })

  it('emits view for the in-progress session too', async () => {
    const { inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    await wrapper.find(`[data-testid="session-header-${inProgressId}"]`).trigger('click')
    expect(wrapper.emitted('view')![0]).toEqual([inProgressId])
  })

  it('shows "Return to current" while read-only, and it emits the current session', async () => {
    const { store, committedId, inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.find('[data-testid="session-return-current"]').exists()).toBe(false)

    // The view flips this after loading the committed session.
    store.viewSession(committedId)
    await flushPromises()

    const control = wrapper.find('[data-testid="session-return-current"]')
    expect(control.exists()).toBe(true)
    await control.trigger('click')
    expect(wrapper.emitted('view')!.at(-1)).toEqual([inProgressId])
  })

  // The operations panel nests under the session it belongs to, so the list
  // reads hierarchically instead of as two sibling panels.
  it('renders the operations slot under the viewed session only', async () => {
    const { store, committedId, inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()

    const inProgressItem = wrapper.find(`[data-testid="session-${inProgressId}"]`)
    expect(inProgressItem.find('[data-testid="ops-panel"]').exists()).toBe(true)
    const committedItem = wrapper.find(`[data-testid="session-${committedId}"]`)
    expect(committedItem.find('[data-testid="ops-panel"]').exists()).toBe(false)

    store.viewSession(committedId)
    await flushPromises()

    expect(
      wrapper.find(`[data-testid="session-${committedId}"]`).find('[data-testid="ops-panel"]').exists()
    ).toBe(true)
    expect(wrapper.findAll('[data-testid="ops-panel"]')).toHaveLength(1)
  })

  it('previews the operation count of sessions that are not in view', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const range = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    const committed = unwrap(await qc.sessions.create(h.id, range))
    await qc.operations.create(h.id, committed.id, [
      { operationType: 'SELECTION' as any, order: 0 },
      { operationType: 'DELETE_POINTS' as any, order: 1 },
    ])
    await qc.sessions.commit(h.id, committed.id)
    await qc.sessions.create(h.id, range)
    await useQcSessionStore().loadSessions(h.id)

    const wrapper = mountList()
    await flushPromises()
    expect(
      wrapper.find(`[data-testid="session-preview-${committed.id}"]`).text()
    ).toContain('2 operations')
  })

  it('says so when a session that is not in view has no operations', async () => {
    const { committedId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.find(`[data-testid="session-preview-${committedId}"]`).text()).toContain(
      'No operations'
    )
  })

  it('still renders the operations slot when there are no sessions', () => {
    const wrapper = mountList()
    expect(wrapper.find('[data-testid="ops-panel"]').exists()).toBe(true)
  })
})
