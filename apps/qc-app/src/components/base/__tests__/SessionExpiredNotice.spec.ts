import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const getAccountLoginUrl = vi.fn((path: string) => `/accounts/login/?next=${path}`)
const hs = ref<any>({ session: { getAccountLoginUrl } })
const sessionExpired = ref(false)
vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({ hs, sessionExpired }),
}))

import SessionExpiredNotice from '@/components/base/SessionExpiredNotice.vue'

// Vuetify's overlay positioning reads it; jsdom doesn't provide one.
vi.stubGlobal(
  'visualViewport',
  Object.assign(new EventTarget(), { width: 1024, height: 768, scale: 1 })
)

const mountNotice = async () => {
  const w = mount(SessionExpiredNotice, {
    attachTo: document.body,
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })
  await flushPromises()
  return w
}

const find = (testId: string) =>
  document.querySelector<HTMLElement>(`[data-testid="${testId}"]`)

beforeEach(() => {
  document.body.innerHTML = ''
  sessionExpired.value = false
  vi.restoreAllMocks()
})

describe('SessionExpiredNotice', () => {
  it('stays hidden while the login is good', async () => {
    await mountNotice()
    expect(find('session-expired')).toBeNull()
  })

  it('tells the user their edits are kept and opens sign-in in a new tab', async () => {
    const open = vi.spyOn(window, 'open').mockReturnValue(null)
    sessionExpired.value = true
    await mountNotice()

    expect(find('session-expired')?.textContent).toContain(
      'Your edits are still here'
    )
    find('session-expired-login')!.click()
    expect(open).toHaveBeenCalledWith(
      '/accounts/login/?next=/qc/',
      '_blank',
      'noopener'
    )
    // Signing in elsewhere leaves the notice up until a save gets through.
    expect(sessionExpired.value).toBe(true)
  })

  it('can be dismissed', async () => {
    sessionExpired.value = true
    await mountNotice()
    find('session-expired-dismiss')!.click()
    expect(sessionExpired.value).toBe(false)
  })
})
