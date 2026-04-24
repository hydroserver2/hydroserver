// Shared Pinia setup for unit tests. No persistedstate plugin.
import { createPinia, setActivePinia, type Pinia } from 'pinia'

export function createTestPinia(): Pinia {
  const pinia = createPinia()
  setActivePinia(pinia)
  return pinia
}
