import { describe, it, expect } from 'vitest'
import { nextTick, ref } from 'vue'
import { useBufferedNumber } from '@/composables/useBufferedNumber'

describe('useBufferedNumber', () => {
  it('seeds the pending buffer from the source ref', () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending } = useBufferedNumber(source, open)
    expect(pending.value).toBe(10_000)
  })

  it('does not propagate edits to source until apply() is called', () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending, apply } = useBufferedNumber(source, open)

    pending.value = 25_000
    expect(source.value).toBe(10_000)

    apply()
    expect(source.value).toBe(25_000)
  })

  it('returns true from apply() on commit, false when the value is invalid', () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending, apply } = useBufferedNumber(source, open, { min: 100 })

    pending.value = 50
    expect(apply()).toBe(false)
    expect(source.value).toBe(10_000)

    pending.value = 5_000
    expect(apply()).toBe(true)
    expect(source.value).toBe(5_000)
  })

  it('isValid reflects the min-bound constraint', () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending, isValid } = useBufferedNumber(source, open, { min: 100 })

    pending.value = 99
    expect(isValid.value).toBe(false)

    pending.value = 100
    expect(isValid.value).toBe(true)

    pending.value = 1_000_000
    expect(isValid.value).toBe(true)
  })

  it('isValid rejects NaN, Infinity, and empty input', () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending, isValid } = useBufferedNumber(source, open, { min: 100 })

    pending.value = Number.NaN
    expect(isValid.value).toBe(false)

    pending.value = Number.POSITIVE_INFINITY
    expect(isValid.value).toBe(false)

    pending.value = ''
    expect(isValid.value).toBe(false)
  })

  it('re-syncs the buffer from source every time the gate opens', async () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending } = useBufferedNumber(source, open)

    // First open: pending starts at the seed value.
    open.value = true
    await nextTick()
    expect(pending.value).toBe(10_000)

    // User edits but doesn't apply.
    pending.value = 999
    open.value = false
    await nextTick()

    // Source unaffected by the unapplied edit.
    expect(source.value).toBe(10_000)

    // Source moves under us (e.g. another consumer updates it).
    source.value = 7_500

    // Re-opening discards the prior pending edit and re-seeds.
    open.value = true
    await nextTick()
    expect(pending.value).toBe(7_500)
  })

  it('treats the gate as edge-triggered: false → false stays put', async () => {
    const source = ref(10_000)
    const open = ref(false)
    const { pending } = useBufferedNumber(source, open)

    pending.value = 1234
    // Setting to the same value (false) doesn't fire the watcher.
    open.value = false
    await nextTick()
    expect(pending.value).toBe(1234)
  })

  it('honours an unbounded source when min is omitted', () => {
    const source = ref(0)
    const open = ref(false)
    const { pending, isValid, apply } = useBufferedNumber(source, open)

    pending.value = -42
    expect(isValid.value).toBe(true)
    expect(apply()).toBe(true)
    expect(source.value).toBe(-42)
  })
})
