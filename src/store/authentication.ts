import { defineStore, storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
// import { User } from '@/types'
import { Provider } from '@/models/settings'
import { api, Snackbar } from '@uwrl/qc-utils'
import router from '@/router/router'
import Storage from '@/utils/storage'
import { useUserStore } from './user'
import { useWorkspaceStore } from './workspaces'
import { useVocabularyStore } from '@/composables/useVocabulary'
import { settings } from '@/config/settings'
import { User } from '@hydroserver/client'

export interface AllAuthFlowItem {
  id: string
  providers?: string[]
}

export const emailStorage = new Storage<string>('unverifiedEmail')

export const useAuthStore = defineStore('authentication', () => {
  /**
   * Persist the state of unverified email since it won't be saved in the db
   * during the verify_email flow. Used on the VerifyEmail.vue page for
   * re-emailing the verification code to the user upon request.
   */
  const unverifiedEmail = ref(emailStorage.get() || '')
  watch(unverifiedEmail, (newEmail) => {
    emailStorage.set(newEmail)
  })

  const isAuthenticated = ref(false)
  const sessionExpiresAt = ref<string | null>(null)

  const flows = ref<AllAuthFlowItem[]>([])
  const flowIds = computed(() => flows.value.map((flow) => flow.id))

  const inEmailVerificationFlow = computed(() =>
    flowIds.value.includes('verify_email')
  )
  const inProviderSignupFlow = computed(() =>
    flowIds.value.includes('provider_signup')
  )

  /**
   * Determines if signing up on the website is available at all.
   * Some organizations will want an admin signing up for their users
   * to be the only way to create an account.
   *
   * Not to be confused with `oAuthProviders.signupEnabled` that tells us if
   * that particular OAuth service can be used to create an account.
   */
  const signupEnabled = ref(false)

  /**
   * An array of OAuth providers that the user can use to authenticate.
   * In some cases, such as with HydroShare, this allows connecting to the provider
   * for data archival instead of direct authentication.
   *
   * This array determines which login with OAuth buttons are available on the login and signup pages.
   */
  const oAuthProviders = ref<Provider[]>([])

  const login = async () => {
    try {
      Snackbar.success('You have logged in!')
      await router.push({ name: 'Sites' })
    } catch (e) {
      console.log('Failed to fetch user info')
    }
  }

  let loggingOut = false
  async function logout() {
    if (loggingOut) return
    try {
      loggingOut = true
      localStorage.clear()
      sessionStorage.clear()
      const response = await api.logout()
      setSession(response)
      await router.push({ name: 'Login' })
    } catch (error) {
      console.error('Error logging out.', error)
    } finally {
      loggingOut = false
    }
  }

  /**
   * Fetches the session variables if there are any and any allowed OAuth methods
   * for this instance of HydroServer.
   */
  async function initializeSession() {
    const vocabularyStore = useVocabularyStore()

    try {
      const [sessionResponse] = await Promise.all([
        api.fetchSession(),
        vocabularyStore.fetchAllVocabularies(),
      ])
      // const authMethodsResponse = await api.fetchAuthMethods()
      // const sessionResponse = await api.fetchSession()

      oAuthProviders.value = settings.authenticationConfiguration.providers
      signupEnabled.value = settings.authenticationConfiguration.hydroserverSignupEnabled
      setSession(sessionResponse)
    } catch (error) {
      console.log('Error initializing session', error)
    }

    if (isAuthenticated.value) {
      try {
        const workspacesResponse = await api.fetchAssociatedWorkspaces()
        const { setWorkspaces } = useWorkspaceStore()
        setWorkspaces(workspacesResponse)
      } catch (error) {
        console.error('Error fetching workspaces', error)
      }
    }
  }

  function setSession(apiResponse: any) {
    const { user } = storeToRefs(useUserStore())
    isAuthenticated.value = apiResponse?.meta?.is_authenticated
    sessionExpiresAt.value = apiResponse?.meta?.expires
    flows.value = apiResponse?.data?.flows || []
    user.value = apiResponse?.data?.account || new User()
  }

  function checkSessionExpiration() {
    if (
      isAuthenticated.value &&
      sessionExpiresAt.value &&
      Date.now() >= new Date(sessionExpiresAt.value).getTime()
    ) {
      Snackbar.info('Session expired. Please log in again.')
      logout()
    }
  }

  // Check if the session has expired when the user switches to this tab
  // and/or when the browser comes into focus
  window.addEventListener('focus', () => {
    checkSessionExpiration()
  })
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      checkSessionExpiration()
    }
  })

  return {
    oAuthProviders,
    signupEnabled,
    isAuthenticated,
    inProviderSignupFlow,
    inEmailVerificationFlow,
    flows,
    unverifiedEmail,
    checkSessionExpiration,
    login,
    logout,
    initializeSession,
    setSession,
  }
})
