import { watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'

declare global {
  interface Window {
    __vbwTestHooks?: {
      waitForSelectedData: (
        minLength?: number,
        timeoutMs?: number
      ) => Promise<number>
    }
  }
}

export function installTestHooks(): void {
  const { selectedData } = storeToRefs(useDataVisStore())

  const waitForSelectedData = (minLength = 1, timeoutMs = 10_000) =>
    new Promise<number>((resolve, reject) => {
      const current = selectedData.value?.length ?? 0
      if (current >= minLength) return resolve(current)

      let stop: ReturnType<typeof watch>

      const timer = setTimeout(() => {
        stop()
        reject(
          new Error(
            `waitForSelectedData: timed out after ${timeoutMs}ms ` +
              `(got ${selectedData.value?.length ?? 0}, expected >= ${minLength})`
          )
        )
      }, timeoutMs)

      stop = watch(
        selectedData,
        (v) => {
          if ((v?.length ?? 0) >= minLength) {
            clearTimeout(timer)
            stop()
            resolve(v!.length)
          }
        },
        { flush: 'post', immediate: true }
      )
    })

  window.__vbwTestHooks = { waitForSelectedData }
}
