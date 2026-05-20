import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useResizable, usePersistedFlag } from '@/composables/useResizable'

// Real `useUiLayoutStore` is fine — it's a tiny pinia store backed by a
// Map and we want to exercise the persistence wiring end-to-end.
import { useUiLayoutStore } from '@/store/uiLayout'

/** Dispatch a fake mouse event with the given coords against window. */
const dispatchMouse = (type: string, x: number, y: number) => {
  const ev = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true })
  window.dispatchEvent(ev)
}

describe('useResizable', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
  })

  it('seeds `size` from `options.initial` when no storageKey is supplied', () => {
    const { size } = useResizable({ initial: 200, min: 100 })
    expect(size.value).toBe(200)
  })

  it('prefers a stored size over `options.initial` when storageKey is set', () => {
    const store = useUiLayoutStore()
    store.setSize('test-key', 350)
    const { size } = useResizable({
      initial: 200,
      min: 100,
      storageKey: 'test-key',
    })
    expect(size.value).toBe(350)
  })

  it('falls back to `options.initial` when the stored size is below `min`', () => {
    const store = useUiLayoutStore()
    // Stored value 50 < min 100 → discarded.
    store.setSize('test-key', 50)
    const { size } = useResizable({
      initial: 200,
      min: 100,
      storageKey: 'test-key',
    })
    expect(size.value).toBe(200)
  })

  it('persists `size` changes back through the layout store when storageKey is set', async () => {
    const store = useUiLayoutStore()
    const { size } = useResizable({
      initial: 200,
      min: 100,
      storageKey: 'persist-key',
    })
    size.value = 275
    await nextTick()
    expect(store.getSize('persist-key')).toBe(275)
  })

  it('does not touch the store when no storageKey is supplied', async () => {
    const store = useUiLayoutStore()
    const before = store.getSize('untracked')
    const { size } = useResizable({ initial: 200, min: 100 })
    size.value = 999
    await nextTick()
    expect(store.getSize('untracked')).toBe(before)
  })

  it('horizontal drag tracks clientX delta and clamps to `min` / `max`', async () => {
    const { size, onStart, dragging } = useResizable({
      initial: 200,
      min: 100,
      max: 400,
    })
    onStart(new MouseEvent('mousedown', { clientX: 500, clientY: 0 }))
    expect(dragging.value).toBe(true)
    expect(document.body.style.userSelect).toBe('none')
    expect(document.body.style.cursor).toBe('col-resize')

    // Move +50 px → size 250 (in range).
    dispatchMouse('mousemove', 550, 0)
    expect(size.value).toBe(250)

    // Move -200 px (relative to start) → size would be 0; clamped to min 100.
    dispatchMouse('mousemove', 300, 0)
    expect(size.value).toBe(100)

    // Move +400 px → size would be 600; clamped to max 400.
    dispatchMouse('mousemove', 900, 0)
    expect(size.value).toBe(400)

    dispatchMouse('mouseup', 900, 0)
    expect(dragging.value).toBe(false)
    expect(document.body.style.userSelect).toBe('')
    expect(document.body.style.cursor).toBe('')
  })

  it('vertical drag tracks clientY delta and sets row-resize cursor', () => {
    const { size, onStart } = useResizable({
      initial: 100,
      min: 50,
      direction: 'vertical',
    })
    onStart(new MouseEvent('mousedown', { clientX: 0, clientY: 100 }))
    expect(document.body.style.cursor).toBe('row-resize')

    dispatchMouse('mousemove', 0, 175)
    expect(size.value).toBe(175)

    dispatchMouse('mouseup', 0, 175)
  })

  it('invert flips the delta sign (sidebar grows when handle moves outward)', () => {
    const { size, onStart } = useResizable({
      initial: 200,
      min: 0,
      invert: true,
    })
    onStart(new MouseEvent('mousedown', { clientX: 500, clientY: 0 }))
    // +100 px movement, inverted → size shrinks by 100.
    dispatchMouse('mousemove', 600, 0)
    expect(size.value).toBe(100)
    dispatchMouse('mouseup', 600, 0)
  })

  it('scales pixel delta to percent when getContainerPx returns > 0', () => {
    const { size, onStart } = useResizable({
      initial: 30,
      min: 0,
      max: 100,
      getContainerPx: () => 1000,
    })
    onStart(new MouseEvent('mousedown', { clientX: 0, clientY: 0 }))
    // 200 px / 1000 px container → +20 percent.
    dispatchMouse('mousemove', 200, 0)
    expect(size.value).toBeCloseTo(50)
    dispatchMouse('mouseup', 200, 0)
  })

  it('treats a non-positive containerPx as the raw-pixel fallback path', () => {
    const { size, onStart } = useResizable({
      initial: 30,
      min: 0,
      max: 1000,
      getContainerPx: () => 0,
    })
    onStart(new MouseEvent('mousedown', { clientX: 0, clientY: 0 }))
    dispatchMouse('mousemove', 200, 0)
    // Raw pixels — no percent scaling.
    expect(size.value).toBe(230)
    dispatchMouse('mouseup', 200, 0)
  })
})

describe('usePersistedFlag', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uses the stored flag value when one exists', () => {
    const store = useUiLayoutStore()
    store.setFlag('flag-key', true)
    const flag = usePersistedFlag('flag-key', false)
    expect(flag.value).toBe(true)
  })

  it('falls back to the initial value when no stored flag exists', () => {
    const flag = usePersistedFlag('untouched', false)
    expect(flag.value).toBe(false)
  })

  it('persists flag changes back through the layout store', async () => {
    const store = useUiLayoutStore()
    const flag = usePersistedFlag('flag-key-2', false)
    flag.value = true
    await nextTick()
    expect(store.getFlag('flag-key-2')).toBe(true)
  })
})
