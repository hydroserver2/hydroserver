import { useVocabularyStore } from '@/composables/useVocabulary'
import { settings } from '@/config/settings'
import { useUserStore } from '@/store/user'
import { useWorkspaceStore } from '@/store/workspaces'
import hs, { createHydroServer, User } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'

const hydroServerHost = import.meta.env.VITE_APP_PROXY_BASE_URL || ''

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

async function initializeAuthenticatedState() {
  const { user } = storeToRefs(useUserStore())
  const workspaceStore = useWorkspaceStore()
  const { setWorkspaces } = workspaceStore

  user.value = new User()
  if (!hs.session.isAuthenticated) return

  const userRequest = hs.user.get().catch((error) => {
    recordInitializationError('Error fetching user', error)
    return null
  })

  const workspacesRequest = hs.workspaces
    .listAllItems({ isAssociated: true })
    .catch((error) => {
      recordInitializationError('Error fetching workspaces', error)
      return null
    })

  const [userResponse, workspacesResponse] = await Promise.all([
    userRequest,
    workspacesRequest,
  ])

  if (userResponse) {
    user.value =
      userResponse.ok && userResponse.status !== 401
        ? userResponse.data
        : new User()
  }

  const previousWorkspaceId = workspaceStore.selectedWorkspace?.id
  if (workspacesResponse) {
    setWorkspaces(workspacesResponse)
    hasBootstrappedWorkspaces.value = true
  }

  if (user.value.isSuperuser === true) {
    // Keep personal workspaces available while the instance-wide list loads.
    const personalWorkspaceId = workspaceStore.selectedWorkspace?.id
    const allWorkspaces = await hs.workspaces
      .listAllItems({})
      .catch((error) => {
        recordInitializationError('Error fetching all workspaces', error)
        return null
      })
    if (allWorkspaces) {
      const restoreSelection =
        workspaceStore.selectedWorkspace?.id === personalWorkspaceId &&
        allWorkspaces.some((workspace) => workspace.id === previousWorkspaceId)
      setWorkspaces(allWorkspaces)
      if (restoreSelection && previousWorkspaceId) {
        workspaceStore.setSelectedWorkspaceById(previousWorkspaceId)
      }
      hasBootstrappedWorkspaces.value = true
    }
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
    csrfCookieName: settings.authenticationConfiguration.csrfCookieName,
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

      const vocabularyRequest = useVocabularyStore()
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
