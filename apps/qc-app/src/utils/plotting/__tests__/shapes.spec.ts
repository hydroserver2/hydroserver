import { describe, it, expect } from 'vitest'
import { composeShapes, withLiveShapes } from '../shapes'

const stage = { name: 'stage', x0: 10, x1: 20 }
const oldWindow = { name: 'edit-window', x0: 100, x1: 200 }
const newWindow = { name: 'edit-window', x0: 300, x1: 400 }

describe('composeShapes', () => {
  it('replaces only the named shapes, after the others by default', () => {
    expect(composeShapes([stage, oldWindow], 'edit-window', [newWindow])).toEqual([
      stage,
      newWindow,
    ])
  })

  it('puts its own shapes first when asked', () => {
    expect(
      composeShapes([oldWindow, stage], 'stage', [stage], { first: true })
    ).toEqual([stage, oldWindow])
  })

  it('handles a plot with no shapes', () => {
    expect(composeShapes(undefined, 'stage', [])).toEqual([])
  })
})

describe('withLiveShapes', () => {
  it('keeps the live stage shape and takes the fresh edit window', () => {
    const layout = { dragmode: 'pan', shapes: [newWindow] } as any
    const merged = withLiveShapes(layout, { shapes: [stage, oldWindow] } as any)
    expect(merged.shapes).toEqual([stage, newWindow])
    expect(merged.dragmode).toBe('pan')
    // The stored layout is not mutated.
    expect(layout.shapes).toEqual([newWindow])
  })

  it('removes the live edit window when the fresh layout has none', () => {
    const merged = withLiveShapes({}, { shapes: [stage, oldWindow] } as any)
    expect(merged.shapes).toEqual([stage])
  })
})
