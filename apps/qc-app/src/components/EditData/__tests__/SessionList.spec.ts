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
  mount(SessionList, { global: { plugins: [pinia, createTestVuetify()] } })

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

  it('clicking a committed session views it read-only', async () => {
    const { store, committedId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    await wrapper.find(`[data-testid="session-${committedId}"]`).trigger('click')
    expect(store.viewedSessionId).toBe(committedId)
    expect(store.isReadOnly).toBe(true)
  })

  it('clicking the current session returns to editing', async () => {
    const { store, committedId, inProgressId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    await wrapper.find(`[data-testid="session-${committedId}"]`).trigger('click')
    expect(store.isReadOnly).toBe(true)
    await wrapper.find(`[data-testid="session-${inProgressId}"]`).trigger('click')
    expect(store.viewedSessionId).toBe(inProgressId)
    expect(store.isReadOnly).toBe(false)
  })

  it('shows a "Return to current" control while viewing read-only', async () => {
    const { committedId } = await seedAndLoad()
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.find('[data-testid="session-return-current"]').exists()).toBe(false)
    await wrapper.find(`[data-testid="session-${committedId}"]`).trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="session-return-current"]').exists()).toBe(true)
  })
})
