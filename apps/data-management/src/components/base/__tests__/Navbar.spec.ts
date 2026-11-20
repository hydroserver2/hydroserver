import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import hs, { User } from '@hydroserver/client'
import { useUserStore } from '@/store/user'
import Navbar from '@/components/base/Navbar.vue'
import MainNavItem from '@/components/base/MainNavItem.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: {}, name: 'Workspaces', path: '/workspaces' }),
}))

vi.mock('@/router/router', () => ({
  default: {
    push: vi.fn(),
    resolve: (to: string) => ({
      path: to,
      meta: {
        requiresAuth: ['/workspaces', '/orchestration/ingestion'].includes(to),
      },
    }),
  },
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ resetState: vi.fn() }),
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    resolveUrl: (path: string) => `https://hydro.example.com${path}`,
    session: {
      get isAuthenticated() {
        return true
      },
      getAccountSignupUrl: () => '',
    },
  },
  User: class {
    firstName = ''
    lastName = ''
    isStaff = false
  },
}))

const ADMIN_URL = 'https://hydro.example.com/admin/'
let resizeNavigation: () => void
const disconnectObserver = vi.fn()

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(hs.session, 'isAuthenticated', 'get').mockReturnValue(true)
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: () => void) {
        resizeNavigation = callback
      }
      observe = vi.fn()
      disconnect = disconnectObserver
    }
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

/** `compact` mirrors the narrow-viewport media query that swaps in the drawer. */
async function mountNavbar(isStaff: boolean, compact = false) {
  const user = new User()
  user.isStaff = isStaff
  useUserStore().user = user

  window.matchMedia = vi.fn().mockReturnValue({
    matches: compact,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })

  const wrapper = shallowMount(Navbar, {
    global: { renderStubDefaultSlot: true, stubs: { RouterLink: true } },
  })
  await nextTick()
  return wrapper
}

describe('Navbar admin dashboard link', () => {
  it('shows staff users the link in the account menu', async () => {
    const wrapper = await mountNavbar(true)

    expect(
      wrapper.get('[data-testid="admin-menu-item"]').attributes('href')
    ).toBe(ADMIN_URL)
  })

  it('shows staff users the link in the compact drawer', async () => {
    const wrapper = await mountNavbar(true, true)

    expect(
      wrapper.get('[data-testid="admin-drawer-item"]').attributes('href')
    ).toBe(ADMIN_URL)
  })

  it('hides the link from non-staff users', async () => {
    for (const compact of [false, true]) {
      const wrapper = await mountNavbar(false, compact)

      expect(wrapper.find('[data-testid^="admin-"]').exists()).toBe(false)
    }
  })
})

describe('Navbar responsive links', () => {
  it('uses the shorter labels and shows About in the main bar', async () => {
    const wrapper = await mountNavbar(false)

    expect(
      wrapper.findAllComponents(MainNavItem).map((item) => item.props('label'))
    ).toEqual([
      'Workspaces',
      'Monitoring Sites',
      'Visualize data',
      'Job orchestration',
      'Quality control',
      'About',
    ])
    expect(wrapper.find('[data-testid="about-menu-item"]').exists()).toBe(false)
  })

  it('moves About into the account menu only while the links do not fit', async () => {
    const wrapper = await mountNavbar(false)
    const container = wrapper.get('.main-navigation').element
    const links = wrapper.get('.main-navigation-links').element
    const about = wrapper.findAll('.main-nav-item-wrapper').at(-1)!
    let availableWidth = 600
    vi.spyOn(container, 'getBoundingClientRect').mockImplementation(
      () => ({ width: availableWidth }) as DOMRect
    )
    vi.spyOn(links, 'getBoundingClientRect').mockReturnValue({
      width: 650,
    } as DOMRect)
    vi.spyOn(about.element, 'getBoundingClientRect').mockReturnValue({
      width: 75,
    } as DOMRect)

    resizeNavigation()
    await nextTick()
    expect(wrapper.find('[data-testid="about-menu-item"]').exists()).toBe(true)
    expect(about.attributes('aria-hidden')).toBe('true')
    expect(about.attributes()).toHaveProperty('inert')

    availableWidth = 550
    resizeNavigation()
    await nextTick()
    expect(wrapper.find('[data-testid="mobile-nav-button"]').exists()).toBe(
      true
    )
    expect(wrapper.get('.navbar-desktop').attributes('aria-hidden')).toBe(
      'true'
    )

    availableWidth = 650
    resizeNavigation()
    await nextTick()
    expect(wrapper.find('[data-testid="about-menu-item"]').exists()).toBe(false)
    expect(about.attributes('aria-hidden')).toBeUndefined()
    expect(about.attributes()).not.toHaveProperty('inert')
    expect(wrapper.find('[data-testid="mobile-nav-button"]').exists()).toBe(
      false
    )

    wrapper.unmount()
    expect(disconnectObserver).toHaveBeenCalled()
  })

  it.each([true, false])(
    'includes About once in the compact drawer (authenticated: %s)',
    async (authenticated) => {
      vi.spyOn(hs.session, 'isAuthenticated', 'get').mockReturnValue(
        authenticated
      )
      const wrapper = await mountNavbar(false, true)

      expect(wrapper.findAll('[data-testid="about-drawer-item"]')).toHaveLength(
        1
      )
      expect(
        wrapper.get('[data-testid="about-drawer-item"]').attributes('to')
      ).toBe('/about')
    }
  )

  it('keeps About in the main bar for signed-out visitors', async () => {
    vi.spyOn(hs.session, 'isAuthenticated', 'get').mockReturnValue(false)
    const wrapper = await mountNavbar(false)

    expect(
      wrapper.findAllComponents(MainNavItem).map((item) => item.props('label'))
    ).toEqual(['Monitoring Sites', 'Visualize data', 'About'])
    expect(wrapper.find('[data-testid="about-menu-item"]').exists()).toBe(false)
  })
})
