import { Snackbar } from '@/utils/notifications'
import hs from '@hydroserver/client'
import { ref, computed } from 'vue'
import { settings } from '@/config/settings'
import { Provider } from '@/models/settings'

export function useHydroShare() {
  const { oAuthProviders } = hs.session

  const connectedProviders = ref<Provider[]>(
    settings.authenticationConfiguration.providers
  )
  const isLoaded = ref(false)

  const hydroShareProvider = computed<Provider | null>(
    () =>
      connectedProviders.value.find(
        (item: any) => item.provider?.id === 'hydroshare'
      ) || null
  )

  const isConnected = computed(() => !!hydroShareProvider.value)

  const isConnectionEnabled = computed(() =>
    oAuthProviders.some((p) => p.id === 'hydroshare' && p.connectEnabled)
  )

  async function connectHydroShare() {
    const callbackUrl = '/profile'
    hs.session.providerRedirect('hydroshare', callbackUrl, 'connect')
  }

  async function disconnectHydroShare() {
    try {
      if (!hydroShareProvider.value) {
        Snackbar.error('Cannot disconnect: no HydroShare provider found.')
        return
      }

      const providerResponse = await hs.session.deleteProvider(
        'hydroshare',
        hydroShareProvider.value.id
      )
      connectedProviders.value = providerResponse.data
      Snackbar.info('Your HydroShare account has been disconnected.')
    } catch (error) {
      console.error('Error disconnecting HydroShare account', error)
      Snackbar.error('Error disconnecting HydroShare account')
    }
  }

  return {
    isLoaded,
    isConnected,
    isConnectionEnabled,
    connectHydroShare,
    disconnectHydroShare,
  }
}
