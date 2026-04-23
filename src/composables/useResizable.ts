import { ref, watch, type Ref } from 'vue'
import { useUiLayoutStore } from '@/store/uiLayout'

export interface UseResizableOptions {
  /** Initial size in px (width for horizontal, height for vertical). */
  initial: number
  /** Minimum size the handle is allowed to produce. */
  min: number
  /** Optional maximum. Omit for unbounded. */
  max?: number
  /**
   * Identifier under which the current size is persisted. Storage is
   * handled by the `uiLayout` pinia store (pinia-plugin-persistedstate)
   * so the sidebar/split layout survives page reloads without any
   * further wiring.
   */
  storageKey?: string
  /** Horizontal drag tracks clientX → width. Vertical tracks clientY
   *  → height. */
  direction?: 'horizontal' | 'vertical'
  /**
   * When `true`, drag delta is negated. Used for sidebars whose
   * drag handle sits on the inner (plot-facing) edge: dragging the
   * handle AWAY from the plot grows the sidebar, so the x-delta
   * needs to flip. Pick the sign that makes "pull the handle
   * outward" grow the panel.
   */
  invert?: boolean
  /**
   * Getter for the container dimension the size is expressed as a
   * fraction of. Used when `size` is a percentage (e.g. the
   * History / OperationPanel vertical split) — without this the
   * raw pixel delta would be added directly to the percent value,
   * making a 30 px drag look like a 30 % swing. We capture the
   * container dimension at drag start and convert pixel delta to
   * "delta percent of container" as the user drags.
   */
  getContainerPx?: () => number
}

export interface UseResizableReturn {
  size: Ref<number>
  /** Bind to the resize handle's `mousedown`. */
  onStart: (event: MouseEvent) => void
  /** True while a drag is in flight — handy for styling the handle
   *  (persistent hover) or pausing other work. */
  dragging: Ref<boolean>
}

/**
 * Generic drag-to-resize helper. Returns a reactive `size` ref and
 * a `mousedown` handler to attach to a resize-grip element.
 * Listeners are attached to `window` for the duration of the drag
 * so the gesture keeps tracking even if the cursor leaves the
 * grip — mirrors how native resize handles behave. `user-select`
 * and `cursor` on `document.body` are toggled for the drag so text
 * doesn't get selected while the user pulls.
 */
export function useResizable(
  options: UseResizableOptions
): UseResizableReturn {
  const direction = options.direction ?? 'horizontal'
  const storageKey = options.storageKey
  const layoutStore = storageKey ? useUiLayoutStore() : null
  let initial = options.initial
  if (storageKey && layoutStore) {
    const stored = layoutStore.getSize(storageKey)
    if (stored != null && stored >= options.min) {
      initial = stored
    }
  }
  const size = ref(initial)
  const dragging = ref(false)

  if (storageKey && layoutStore) {
    watch(size, (v) => layoutStore.setSize(storageKey, v))
  }

  const onStart = (e: MouseEvent) => {
    e.preventDefault()
    const startCoord = direction === 'vertical' ? e.clientY : e.clientX
    const startSize = size.value
    // Capture the container dimension ONCE per drag so size updates
    // stay linear even if the page relayouts mid-gesture. Falling
    // back to 0 disables the scaling path and the delta is applied
    // raw as pixels.
    const containerPx = Math.max(0, options.getContainerPx?.() ?? 0)
    dragging.value = true

    const onMove = (ev: MouseEvent) => {
      const coord = direction === 'vertical' ? ev.clientY : ev.clientX
      let delta = coord - startCoord
      if (options.invert) delta = -delta
      // Convert pixel delta to percent-of-container when the caller
      // wants `size` interpreted as a percentage.
      if (containerPx > 0) delta = (delta / containerPx) * 100
      let next = startSize + delta
      if (next < options.min) next = options.min
      if (options.max != null && next > options.max) next = options.max
      size.value = next
    }
    const onEnd = () => {
      dragging.value = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onEnd)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onEnd)
    document.body.style.userSelect = 'none'
    document.body.style.cursor =
      direction === 'vertical' ? 'row-resize' : 'col-resize'
  }

  return { size, onStart, dragging }
}

/** Persisted boolean flag — mirrors `useResizable`'s storage story
 *  for the collapse toggles so they survive reloads alongside the
 *  sibling widths. */
export function usePersistedFlag(
  storageKey: string,
  initial: boolean
): Ref<boolean> {
  const layoutStore = useUiLayoutStore()
  const stored = layoutStore.getFlag(storageKey)
  const flag = ref(stored ?? initial)
  watch(flag, (v) => layoutStore.setFlag(storageKey, v))
  return flag
}
