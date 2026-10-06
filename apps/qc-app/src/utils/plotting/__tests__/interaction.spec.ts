import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('plotly.js-dist', () => ({
  default: {
    relayout: vi.fn(),
  },
}))

// Imported up front so building the module graph doesn't count against
// a test's timeout.
import * as mod from '@/utils/plotting/interaction'

describe('plotting/interaction exports', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('exports all six interaction symbols as functions', () => {
    expect(typeof mod.handleMouseMove).toBe('function')
    expect(typeof mod.handleMouseOut).toBe('function')
    expect(typeof mod.handleWheel).toBe('function')
    expect(typeof mod.widenYAxisDragRects).toBe('function')
    expect(typeof mod.suppressHiddenAxisDragRects).toBe('function')
    expect(typeof mod.updateAxisChips).toBe('function')
  })

  it('updateAxisChips(null) does not throw', () => {
    const { updateAxisChips } = mod
    expect(() => updateAxisChips(null)).not.toThrow()
  })
})
