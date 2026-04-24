import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('plotly.js-dist', () => ({
  default: {
    newPlot: vi.fn(),
    update: vi.fn(),
    restyle: vi.fn(),
    relayout: vi.fn(),
  },
}))

describe('plotting/events exports', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('exports handleClick as a function', async () => {
    const { handleClick } = await import('@/utils/plotting/events')
    expect(typeof handleClick).toBe('function')
  })

  it('exports handleNewPlot as a function', async () => {
    const { handleNewPlot } = await import('@/utils/plotting/events')
    expect(typeof handleNewPlot).toBe('function')
  })
})
