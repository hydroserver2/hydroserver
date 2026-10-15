/**
 * Native browser confirmation while the given flag is true, so a refresh
 * mid-edit can't silently drop edits that never reached the server.
 * Browsers ignore custom messages and only prompt after user interaction.
 */

import { onMounted, onUnmounted, type Ref } from 'vue'

export function useUnsavedChangesWarning(hasUnsavedChanges: Ref<boolean>) {
  function onBeforeUnload(event: BeforeUnloadEvent) {
    if (!hasUnsavedChanges.value) return
    event.preventDefault()
    // Legacy browsers gate the prompt on a non-empty returnValue.
    event.returnValue = ''
  }

  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onUnmounted(() => window.removeEventListener('beforeunload', onBeforeUnload))

  return { onBeforeUnload }
}
