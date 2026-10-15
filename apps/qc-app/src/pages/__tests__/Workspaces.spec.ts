import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive, ref } from 'vue'
import { createTestVuetify } from '@/utils/test/vuetify'
import { useWorkspaceStore } from '@/store/workspaces'
import Workspaces from '../Workspaces.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const push = vi.fn()
const route = reactive<{ query: Record<string, unknown> }>({ query: {} })
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => route,
}))

const WS_A = { id: 'ws-a', name: 'Alpha', isPrivate: false, collaboratorRole: null }
const WS_B = { id: 'ws-b', name: 'Beta', isPrivate: true, collaboratorRole: null }
const hs = ref<any>({
  workspaces: { list: vi.fn(async () => ({ ok: true, data: [WS_A, WS_B] })) },
  datastreams: { list: vi.fn(async () => ({ ok: true, data: [] })) },
  resultQualifiers: { list: vi.fn(async () => ({ ok: true, data: [] })) },
})
vi.mock('@/store/hydroserver', () => ({ useHydroServer: () => ({ hs }) }))
vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({ roleName: () => 'owner', canEdit: () => true }),
}))

let pinia: ReturnType<typeof createPinia>

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  push.mockClear()
  route.query = {}
})

const mountPage = async () => {
  const wrapper = mount(Workspaces, {
    global: { plugins: [createTestVuetify(), pinia] },
  })
  await flushPromises()
  return wrapper
}

const pickButton = (wrapper: any, id: string) =>
  wrapper.find(`[data-testid="workspace-pick-${id}"]`)

describe('Workspaces page', () => {
  it('offers Continue on the current workspace and returns to the app', async () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = WS_A as any
    const wrapper = await mountPage()

    const button = pickButton(wrapper, 'ws-a')
    expect(button.text()).toContain('Continue')
    expect(button.attributes('disabled')).toBeUndefined()
    await button.trigger('click')

    expect(push).toHaveBeenCalledWith({ name: 'Home' })
    expect(store.selectedWorkspace?.id).toBe('ws-a')
  })

  it('labels the other workspaces Select', async () => {
    useWorkspaceStore().selectedWorkspace = WS_A as any
    const wrapper = await mountPage()
    expect(pickButton(wrapper, 'ws-b').text()).toBe('Select')
  })

  it('names the current workspace in a hint', async () => {
    useWorkspaceStore().selectedWorkspace = WS_A as any
    const wrapper = await mountPage()
    expect(
      wrapper.find('[data-testid="workspace-current-hint"]').text()
    ).toContain('Alpha')
  })

  it('shows no hint and no Continue without a selection', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="workspace-current-hint"]').exists()).toBe(false)
    expect(pickButton(wrapper, 'ws-a').text()).toBe('Select')
  })

  it('returns to a path given in next', async () => {
    route.query = { next: '/some/page' }
    const wrapper = await mountPage()
    await pickButton(wrapper, 'ws-b').trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/some/page' })
  })
})
