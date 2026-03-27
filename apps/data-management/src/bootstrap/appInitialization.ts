import { useVocabularyStore } from '@/composables/useVocabulary'
import pinia from '@/plugins/pinia'
import { useUserStore } from '@/store/user'
import { useWorkspaceStore } from '@/store/workspaces'
import hs, { createHydroServer, User } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'

const hydroServerHost =
  import.meta.env.VITE_APP_PROXY_BASE_URL ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

const isHydroServerInitializing = ref(false)
export const isHydroServerReady = ref(false)
export const isAppInitializing = ref(false)
export const hasBootstrappedWorkspaces = ref(false)
export const initializationError = ref<unknown>(null)

let hydroServerInitializationPromise: Promise<void> | null = null
let appInitializationPromise: Promise<void> | null = null

function recordInitializationError(message: string, error: unknown) {
  console.error(message, error)
  if (initializationError.value == null) {
    initializationError.value = error
  }
}

export async function initializeAuthenticatedState() {
  const { user } = storeToRefs(useUserStore(pinia))
  const { setWorkspaces } = useWorkspaceStore(pinia)

  user.value = new User()
  setWorkspaces([])
  hasBootstrappedWorkspaces.value = false

  if (!hs.session.isAuthenticated) return

  const userRequest = hs.user.get().catch((error) => {
    recordInitializationError('Error fetching user', error)
    return null
  })

  const workspacesRequest = hs.workspaces
    .listAllItems({
      is_associated: true,
      expand_related: true,
    })
    .catch((error) => {
      recordInitializationError('Error fetching workspaces', error)
      return null
    })

  const [userResponse, workspacesResponse] = await Promise.all([
    userRequest,
    workspacesRequest,
  ])

  if (userResponse) {
    user.value = userResponse.status === 401 ? new User() : userResponse.data
  }

  if (workspacesResponse) {
    setWorkspaces(workspacesResponse)
    hasBootstrappedWorkspaces.value = true
  }
}

export function startAppInitialization() {
  if (appInitializationPromise) return appInitializationPromise

  initializationError.value = null
  isHydroServerInitializing.value = true
  isHydroServerReady.value = false
  isAppInitializing.value = true
  hasBootstrappedWorkspaces.value = false

  hydroServerInitializationPromise = createHydroServer({
    host: hydroServerHost,
    oidc: {
      clientId:
        import.meta.env.VITE_OIDC_CLIENT_ID || 'hydroserver-data-management',
      redirectPath: import.meta.env.VITE_OIDC_REDIRECT_PATH || '/callback',
      postLogoutRedirectPath:
        import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_PATH || '/',
      scope: import.meta.env.VITE_OIDC_SCOPE || 'openid profile email',
    },
  })
    .then(() => {
      isHydroServerReady.value = true
    })
    .catch((error) => {
      recordInitializationError('Error initializing HydroServer client', error)
    })
    .finally(() => {
      isHydroServerInitializing.value = false
    })

  appInitializationPromise = hydroServerInitializationPromise
    .then(async () => {
      if (!isHydroServerReady.value) return

      const vocabularyRequest = useVocabularyStore(pinia)
        .fetchAllVocabularies()
        .catch((error) => {
          recordInitializationError('Error fetching vocabularies', error)
        })

      await Promise.all([vocabularyRequest, initializeAuthenticatedState()])
    })
    .finally(() => {
      isAppInitializing.value = false
    })

  return appInitializationPromise
}

export function waitForHydroServerInitialization() {
  return hydroServerInitializationPromise ?? Promise.resolve()
}
