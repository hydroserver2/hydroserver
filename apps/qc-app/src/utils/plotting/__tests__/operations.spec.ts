import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('plotly.js-dist', () => ({
  default: {
    relayout: vi.fn(),
    restyle: vi.fn(),
    update: vi.fn(),
    newPlot: vi.fn(),
  },
}))

describe('plotting/operations exports', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('exports all 9 operation symbols as functions', async () => {
    const mod = await import('@/utils/plotting/operations')
    expect(typeof mod.zoomXaxisTo).toBe('function')
    expect(typeof mod.toggleTraceVisibility).toBe('function')
    expect(typeof mod.toggleAxisVisibility).toBe('function')
    expect(typeof mod.setSelectedPoints).toBe('function')
    expect(typeof mod.clearSelection).toBe('function')
    expect(typeof mod.applyTraceUpdate).toBe('function')
    expect(typeof mod.cropXaxisRange).toBe('function')
    expect(typeof mod.fitXaxisToVisible).toBe('function')
    expect(typeof mod.fitYaxisToVisible).toBe('function')
  })

  it('null-arg calls do not throw', async () => {
    const {
      zoomXaxisTo,
      setSelectedPoints,
      clearSelection,
      applyTraceUpdate,
    } = await import('@/utils/plotting/operations')

    await expect(zoomXaxisTo(null, 0, 1)).resolves.not.toThrow()
    await expect(setSelectedPoints(null, 0, [])).resolves.not.toThrow()
    await expect(clearSelection(null, 0)).resolves.not.toThrow()
    await expect(
      applyTraceUpdate(null, {}, {})
    ).resolves.not.toThrow()
  })
})
