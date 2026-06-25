import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('plotly.js-dist', () => ({
  default: {
    relayout: vi.fn(),
  },
}))

describe('plotting/interaction exports', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('exports all six interaction symbols as functions', async () => {
    const mod = await import('@/utils/plotting/interaction')
    expect(typeof mod.handleMouseMove).toBe('function')
    expect(typeof mod.handleMouseOut).toBe('function')
    expect(typeof mod.handleWheel).toBe('function')
    expect(typeof mod.widenYAxisDragRects).toBe('function')
    expect(typeof mod.suppressHiddenAxisDragRects).toBe('function')
    expect(typeof mod.updateAxisChips).toBe('function')
  })

  it('updateAxisChips(null) does not throw', async () => {
    const { updateAxisChips } = await import('@/utils/plotting/interaction')
    expect(() => updateAxisChips(null)).not.toThrow()
  })
})
