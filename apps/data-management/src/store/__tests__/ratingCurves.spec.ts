import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useRatingCurveStore } from '../ratingCurves'

const {
  createMock,
  deleteMock,
  listItemsForThingMock,
  updateMock,
} = vi.hoisted(() => ({
  createMock: vi.fn(),
  deleteMock: vi.fn(),
  listItemsForThingMock: vi.fn(),
  updateMock: vi.fn(),
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    ratingCurves: {
      create: createMock,
      delete: deleteMock,
      listItemsForThing: listItemsForThingMock,
      update: updateMock,
    },
  },
}))

describe('rating curve store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    createMock.mockReset()
    deleteMock.mockReset()
    listItemsForThingMock.mockReset()
    updateMock.mockReset()
    listItemsForThingMock.mockResolvedValue([])
    createMock.mockResolvedValue({ ok: true, data: { id: 'created-1' } })
    updateMock.mockResolvedValue({ ok: true, data: { id: 'curve-1' } })
    deleteMock.mockResolvedValue({ ok: true, data: null })
  })

  it('creates rating curves as database records with points', async () => {
    const store = useRatingCurveStore()
    store.queueRatingCurveCreate(
      'Stage discharge',
      'Imported from CSV',
      'power_law',
      [
        [1, 2],
        [2, 4],
      ],
      [
        { inputValue: '1', outputValue: '2' },
        { inputValue: '2', outputValue: '4' },
      ]
    )

    const result = await store.updateRatingCurves('thing-1')

    expect(result.ok).toBe(true)
    expect(createMock).toHaveBeenCalledWith({
      id: '',
      name: 'Stage discharge',
      description: 'Imported from CSV',
      fittingMethod: 'power_law',
      thingId: 'thing-1',
      points: [
        [1, 2],
        [2, 4],
      ],
    })
    expect(store.pendingCreates).toHaveLength(0)
  })

  it('updates rating curve metadata and points through the rating curve API', async () => {
    listItemsForThingMock.mockResolvedValueOnce([
      {
        id: 'curve-1',
        name: 'Old curve',
        description: null,
        fittingMethod: 'linear',
        points: [[0, 0]],
      },
    ])
    const store = useRatingCurveStore()
    await store.loadExistingRatingCurves('thing-1')

    store.queueExistingRatingCurveMetadataUpdate(
      'curve-1',
      'New curve',
      'Updated notes',
      'power_law'
    )
    store.queueExistingRatingCurveReplace(
      'curve-1',
      [[1, 3]],
      [{ inputValue: '1', outputValue: '3' }]
    )

    const result = await store.updateRatingCurves('thing-1')

    expect(result.ok).toBe(true)
    expect(updateMock).toHaveBeenCalledWith({
      id: 'curve-1',
      name: 'New curve',
      description: 'Updated notes',
      fittingMethod: 'power_law',
      points: [[1, 3]],
    })
    expect(store.pendingMetadataUpdates).toHaveLength(0)
    expect(store.pendingReplaces).toHaveLength(0)
  })

  it('retains failed creates so users can retry without losing edits', async () => {
    createMock.mockResolvedValueOnce({
      ok: false,
      message: 'Duplicate input_value in points.',
    })
    const store = useRatingCurveStore()
    const tempId = store.queueRatingCurveCreate(
      'Bad curve',
      '',
      'linear',
      [
        [1, 2],
        [1, 3],
      ],
      [
        { inputValue: '1', outputValue: '2' },
        { inputValue: '1', outputValue: '3' },
      ]
    )

    const result = await store.updateRatingCurves('thing-1')

    expect(result.ok).toBe(false)
    expect(result.failedCreates).toEqual([
      {
        tempId,
        name: 'Bad curve',
        message: 'Duplicate input_value in points.',
      },
    ])
    expect(store.pendingCreates.map((item) => item.tempId)).toEqual([tempId])
  })

  it('deletes rating curves by rating curve id', async () => {
    const store = useRatingCurveStore()
    store.queueExistingRatingCurveDelete('curve-1')

    const result = await store.updateRatingCurves('thing-1')

    expect(result.ok).toBe(true)
    expect(deleteMock).toHaveBeenCalledWith('curve-1')
    expect(store.pendingDeleteIds).toHaveLength(0)
  })
})
