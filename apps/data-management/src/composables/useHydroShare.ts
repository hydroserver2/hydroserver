import hs from '@hydroserver/client'
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { settings } from '@/config/settings'
import { Provider } from '@/models/settings'
import { useUserStore } from '@/store/user'

const availableProviders = ref<Provider[]>(
  settings.authenticationConfiguration.providers
)
const isLoaded = ref(true)

export function useHydroShare() {
  const { user } = storeToRefs(useUserStore())

  const availableHydroShareProvider = computed<Provider | null>(
    () => availableProviders.value.find((item) => item.id === 'hydroshare') || null
  )

  const isConnectionEnabled = computed(() =>
    Boolean(availableHydroShareProvider.value?.connectEnabled)
  )

  const isConnected = computed(() => Boolean(user.value?.hydroShareConnected))

  function manageHydroShareConnection() {
    window.location.assign(hs.session.accountProfileUrl)
  }

  return {
    isLoaded,
    isConnectionEnabled,
    isConnected,
    manageHydroShareConnection,
  }
}
