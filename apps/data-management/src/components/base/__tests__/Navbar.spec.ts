import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { User } from '@hydroserver/client'
import { useUserStore } from '@/store/user'
import Navbar from '@/components/base/Navbar.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: {}, name: 'Workspaces', path: '/workspaces' }),
}))

vi.mock('@/router/router', () => ({
  default: {
    push: vi.fn(),
    resolve: () => ({ meta: {} }),
  },
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ resetState: vi.fn() }),
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    resolveUrl: (path: string) => `https://hydro.example.com${path}`,
    session: {
      isAuthenticated: true,
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
    global: { renderStubDefaultSlot: true },
  })
  await nextTick()
  return wrapper
}

describe('Navbar admin dashboard link', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

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
