import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// --- Mocks --------------------------------------------------------------

const plotlyMock = vi.hoisted(() => ({
  relayout: vi.fn(),
  deleteTraces: vi.fn().mockResolvedValue(undefined),
  addTraces: vi.fn().mockResolvedValue(undefined),
}))
vi.mock('plotly.js-dist', () => ({ default: plotlyMock }))

const plotlyRef = ref<any>(null)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ plotlyRef }),
}))

import {
  setStageShape,
  clearStageShape,
  stagePanMode,
} from '../staging'

// Real Plotly mutates `gd.layout` in place on every relayout call; the
// stub mirrors that so the next flush's "read the live shapes" step sees
// what the previous flush wrote.
const applyRelayout = (root: any, update: any) => {
  root.layout = root.layout ?? {}
  if (update && Object.prototype.hasOwnProperty.call(update, 'shapes')) {
    root.layout.shapes = update.shapes
  }
  if (update && Object.prototype.hasOwnProperty.call(update, 'dragmode')) {
    root.layout.dragmode = update.dragmode
  }
  return Promise.resolve()
}

describe('staging shape merging', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    plotlyMock.relayout.mockImplementation(applyRelayout)
    stagePanMode.value = true
    plotlyRef.value = {
      layout: {
        dragmode: 'pan',
        shapes: [{ name: 'edit-window', x0: 100, x1: 200, yref: 'paper' }],
      },
    }
  })

  it('keeps the edit-window shape alongside the stage shape when showing the stage band', async () => {
    await setStageShape(10, 20)

    const lastCall = plotlyMock.relayout.mock.calls.at(-1)
    const shapes = lastCall![1].shapes as any[]
    expect(shapes.some((s) => s.name === 'edit-window')).toBe(true)
    expect(shapes.some((s) => s.name === 'stage')).toBe(true)
    // Untouched by the merge.
    const editWindow = shapes.find((s) => s.name === 'edit-window')
    expect(editWindow.x0).toBe(100)
    expect(editWindow.x1).toBe(200)
  })

  it('keeps the edit-window shape after clearing the stage shape', async () => {
    await setStageShape(10, 20)
    await clearStageShape()

    const lastCall = plotlyMock.relayout.mock.calls.at(-1)
    const shapes = lastCall![1].shapes as any[]
    expect(shapes.some((s) => s.name === 'edit-window')).toBe(true)
    expect(shapes.some((s) => s.name === 'stage')).toBe(false)
  })

  it('does not duplicate the stage shape across repeated setStageShape calls', async () => {
    await setStageShape(10, 20)
    await setStageShape(30, 40)

    const lastCall = plotlyMock.relayout.mock.calls.at(-1)
    const shapes = lastCall![1].shapes as any[]
    expect(shapes.filter((s) => s.name === 'stage').length).toBe(1)
    expect(shapes.find((s) => s.name === 'stage').x0).toBe(30)
  })
})
