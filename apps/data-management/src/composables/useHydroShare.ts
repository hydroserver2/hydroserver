import hs from '@hydroserver/client'
import { ref, computed } from 'vue'
import { settings } from '@/config/settings'
import { Provider } from '@/models/settings'

const availableProviders = ref<Provider[]>(
  settings.authenticationConfiguration.providers
)
const isLoaded = ref(true)

export function useHydroShare() {
  const availableHydroShareProvider = computed<Provider | null>(
    () => availableProviders.value.find((item) => item.id === 'hydroshare') || null
  )

  const isConnectionEnabled = computed(() =>
    Boolean(availableHydroShareProvider.value?.connectEnabled)
  )

  function manageHydroShareConnection() {
    window.location.assign(hs.session.accountProfileUrl)
  }

  return {
    isLoaded,
    isConnectionEnabled,
    manageHydroShareConnection,
  }
}
