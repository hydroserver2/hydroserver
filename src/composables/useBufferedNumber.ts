import { computed, ref, watch, type Ref } from 'vue'

/**
 * Two-stage edit buffer over a numeric ref. Bind your input to
 * `pending` so per-keystroke writes don't bounce the underlying
 * `source` — only `apply()` (or whatever your UI wires it to) commits.
 *
 * `gateOpen` re-syncs the buffer from `source` every time it
 * transitions from false → true, so opening a popover always shows
 * the current source value, and closing without applying discards
 * any in-progress edit.
 *
 * `min` rejects values below the threshold; `apply()` is a no-op when
 * `pending` isn't a finite number ≥ min, and `isValid` reflects that
 * for the caller's disabled-state binding.
 */
export function useBufferedNumber(
  source: Ref<number>,
  gateOpen: Ref<boolean>,
  options: { min?: number } = {}
) {
  const min = options.min ?? -Infinity
  const pending = ref<number | string>(source.value)

  watch(gateOpen, (open) => {
    if (open) pending.value = source.value
  })

  const isValid = computed(() => {
    const n = Number(pending.value)
    return Number.isFinite(n) && n >= min
  })

  const apply = () => {
    if (!isValid.value) return false
    source.value = Number(pending.value)
    return true
  }

  return { pending, isValid, apply }
}
