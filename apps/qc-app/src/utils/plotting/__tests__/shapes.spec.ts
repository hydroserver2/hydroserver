import { describe, it, expect } from 'vitest'
import { withLiveShapes } from '../shapes'

const stage = { name: 'stage', x0: 10, x1: 20 }

describe('withLiveShapes', () => {
  it('carries the live shapes onto a fresh layout', () => {
    const layout = { dragmode: 'pan' } as any
    const merged = withLiveShapes(layout, { shapes: [stage] } as any)
    expect(merged.shapes).toEqual([stage])
    expect(merged.dragmode).toBe('pan')
    // The stored layout is not mutated.
    expect(layout.shapes).toBeUndefined()
  })

  it('handles a plot with no shapes', () => {
    expect(withLiveShapes({}, undefined).shapes).toEqual([])
  })
})
