import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import VerifyEmail from '@/pages/account/VerifyEmail.vue'
import { useUserStore } from '@/store/user'

const mocks = vi.hoisted(() => ({
  router: {
    push: vi.fn(),
  },
  snackbar: {
    success: vi.fn(),
    error: vi.fn(),
  },
  hs: {
    session: {
      unverifiedEmail: 'new-user@example.com',
    },
    user: {
      verifyEmailWithCode: vi.fn(),
      get: vi.fn(),
      sendVerificationEmail: vi.fn(),
    },
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => mocks.router,
}))

vi.mock('@/utils/notifications', () => ({
  Snackbar: mocks.snackbar,
}))

vi.mock('@hydroserver/client', () => ({
  default: mocks.hs,
  User: class User {
    email = ''
    accountType = 'standard'
  },
}))

describe('VerifyEmail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mocks.hs.user.verifyEmailWithCode.mockResolvedValue({
      ok: true,
      message: 'OK',
    })
    mocks.hs.user.get.mockResolvedValue({
      ok: true,
      status: 200,
      data: { email: 'new-user@example.com', accountType: 'standard' },
    })
  })

  it('refreshes the user store after email verification', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const userStore = useUserStore()

    const wrapper = shallowMount(VerifyEmail, {
      global: {
        plugins: [pinia],
      },
    })
    const vm = wrapper.vm as unknown as {
      verificationCode: string
      verifyCode: () => Promise<void>
    }

    vm.verificationCode = '123456'
    await vm.verifyCode()

    expect(mocks.hs.user.verifyEmailWithCode).toHaveBeenCalledWith('123456')
    expect(mocks.hs.user.get).toHaveBeenCalled()
    expect(userStore.user.email).toBe('new-user@example.com')
    expect(mocks.router.push).toHaveBeenCalledWith({ name: 'Sites' })
  })
})
