import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, reactive, ref, type Ref } from 'vue'

const state = vi.hoisted(() => ({
  bootstrap: {} as {
    isHydroServerReady: Ref<boolean>
    isAccessContextReady: Ref<boolean>
    accessContextError: Ref<unknown>
    initializationError: Ref<unknown>
  },
  route: {} as { meta: { requiresAuth: boolean } },
}))
state.route = reactive({ meta: { requiresAuth: true } })
state.bootstrap = {
  isHydroServerReady: ref(true),
  isAccessContextReady: ref(false),
  accessContextError: ref(null),
  initializationError: ref(null),
}
vi.mock('@/bootstrap/appInitialization', () => state.bootstrap)
vi.mock('vue-router', () => ({ useRoute: () => state.route }))
vi.mock('@/components/base/Navbar.vue', () => ({
  default: { template: '<nav />' },
}))
vi.mock('@/components/base/Footer.vue', () => ({
  default: { template: '<footer />' },
}))
vi.mock('@/components/base/Notifications.vue', () => ({
  default: { template: '<div />' },
}))

const pageMounted = vi.fn()
const protectedPage = defineComponent({
  setup() {
    pageMounted()
  },
  template: '<section>Workspace content</section>',
})

async function mountApp() {
  const { default: App } = await import('../App.vue')
  return mount(App, {
    global: {
      stubs: {
        'router-view': {
          setup: () => ({ page: protectedPage }),
          template: '<slot :Component="page" />',
        },
        'v-app': { template: '<div><slot /></div>' },
        'v-main': { template: '<main><slot /></main>' },
        HsFullScreenLoader: { template: '<div>Loading HydroServer...</div>' },
        HsEmptyState: {
          props: ['title'],
          template:
            '<section><h2>{{ title }}</h2><slot /><slot name="actions" /></section>',
        },
        'v-btn-page-action': { template: '<button><slot /></button>' },
        'v-btn-cancel': { template: '<a><slot /></a>' },
      },
    },
  })
}

beforeEach(() => {
  pageMounted.mockClear()
  state.route.meta.requiresAuth = true
  state.bootstrap.isHydroServerReady.value = true
  state.bootstrap.isAccessContextReady.value = false
  state.bootstrap.accessContextError.value = null
  state.bootstrap.initializationError.value = null
})

describe('protected page startup', () => {
  it('defers permission checks until the user and workspace context is ready', async () => {
    const wrapper = await mountApp()
    expect(wrapper.text()).toContain('Loading HydroServer...')
    expect(pageMounted).not.toHaveBeenCalled()

    state.bootstrap.isAccessContextReady.value = true
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Workspace content')
    expect(pageMounted).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('offers recovery for failed access requests without mounting the protected page', async () => {
    state.bootstrap.accessContextError.value = new Error('Network unavailable')
    const wrapper = await mountApp()
    expect(wrapper.text()).toContain('Unable to load HydroServer')
    expect(wrapper.text()).toContain('Try again')
    expect(wrapper.text()).toContain('Browse monitoring sites')
    expect(pageMounted).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('keeps public pages available while access context is loading or failed', async () => {
    state.route.meta.requiresAuth = false
    state.bootstrap.accessContextError.value = new Error('Network unavailable')
    const wrapper = await mountApp()
    expect(wrapper.text()).toContain('Workspace content')
    expect(pageMounted).toHaveBeenCalledTimes(1)

    state.route.meta.requiresAuth = true
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Unable to load HydroServer')
    expect(wrapper.text()).not.toContain('Workspace content')
    wrapper.unmount()
  })
})
