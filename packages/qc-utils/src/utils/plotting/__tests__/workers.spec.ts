/**
 * Wiring smoke tests for every `*.worker.ts` module.
 *
 * The algorithmic behaviour of each kernel is covered in
 * `operation-cores.spec.ts`, so these tests only verify the worker
 * handler is installed and forwards its payload to its core — i.e. the
 * thin shell is plumbed correctly. Two workers still carry inline
 * logic that has no core counterpart (`drift-correction.worker.ts` and
 * `shift-datetimes.worker.ts`), so we keep behavioural assertions for
 * those.
 *
 * Each worker file registers its handler via `self.onmessage = ...` at
 * module evaluation time. We import each module once, capture its
 * handler, and invoke it synchronously with `self.postMessage`
 * redirected to a local capture buffer. `self` resolves to the global
 * `Window` under happy-dom.
 */

import { describe, expect, it } from 'vitest'

type Handler = (e: { data: any }) => void

async function loadWorker(importFn: () => Promise<unknown>) {
  ;(self as any).onmessage = null
  ;(self as any).postMessage = () => {}
  await importFn()
  const handler = (self as any).onmessage as Handler
  if (!handler) throw new Error('Worker module did not set self.onmessage')
  return (data: any): any[] => {
    const posted: any[] = []
    ;(self as any).postMessage = (msg: any) => posted.push(msg)
    handler({ data })
    return posted
  }
}

// Workers are imported sequentially; each overwrites self.onmessage, so grabbing
// it immediately is mandatory.
const invokeDelete = await loadWorker(() => import('../delete-data.worker'))
const invokeAdd = await loadWorker(() => import('../add-data.worker'))
const invokeChangeValues = await loadWorker(
  () => import('../change-values.worker')
)
const invokeChange = await loadWorker(() => import('../change.worker'))
const invokeRateOfChange = await loadWorker(
  () => import('../rate-of-change.worker')
)
const invokeFindGaps = await loadWorker(() => import('../find-gaps.worker'))
const invokePersistence = await loadWorker(
  () => import('../persistence.worker')
)
const invokeFillGaps = await loadWorker(() => import('../fill-gaps.worker'))
const invokeInterpolate = await loadWorker(
  () => import('../interpolate.worker')
)
const invokeValueThreshold = await loadWorker(
  () => import('../value-threshold.worker')
)
const invokeShiftDatetimes = await loadWorker(
  () => import('../shift-datetimes.worker')
)
const invokeDriftCorrection = await loadWorker(
  () => import('../drift-correction.worker')
)

function bufferX(values: number[]): SharedArrayBuffer {
  const buf = new SharedArrayBuffer(values.length * Float64Array.BYTES_PER_ELEMENT)
  new Float64Array(buf).set(values)
  return buf
}
function bufferY(values: number[]): SharedArrayBuffer {
  const buf = new SharedArrayBuffer(values.length * Float64Array.BYTES_PER_ELEMENT)
  new Float64Array(buf).set(values)
  return buf
}
function emptyBufferX(length: number): SharedArrayBuffer {
  return new SharedArrayBuffer(length * Float64Array.BYTES_PER_ELEMENT)
}
function emptyBufferY(length: number): SharedArrayBuffer {
  return new SharedArrayBuffer(length * Float64Array.BYTES_PER_ELEMENT)
}

// ---------------------------------------------------------------------
// Cores-backed wrappers — verify the handler runs and hands off to its
// core. Behavioural coverage lives in `operation-cores.spec.ts`.
// ---------------------------------------------------------------------

describe('core-backed worker wiring', () => {
  it('delete-data.worker posts Done and writes through to the output', () => {
    const outX = emptyBufferX(2)
    const outY = emptyBufferY(2)
    const posted = invokeDelete({
      bufferX: bufferX([10, 20, 30]),
      bufferY: bufferY([1, 2, 3]),
      outputBufferX: outX,
      outputBufferY: outY,
      start: 0,
      end: 2,
      deleteSegment: [1],
      startTarget: 0,
    })
    expect(posted).toEqual(['Done'])
    expect(Array.from(new Float64Array(outX))).toEqual([10, 30])
  })

  it('add-data.worker posts Done and writes merged output', () => {
    const outX = emptyBufferX(3)
    const outY = emptyBufferY(3)
    const posted = invokeAdd({
      bufferX: bufferX([10, 30]),
      bufferY: bufferY([1, 3]),
      outputBufferX: outX,
      outputBufferY: outY,
      origStart: 0,
      origEnd: 2,
      insertions: [[20, 2]],
      outStart: 0,
    })
    expect(posted).toEqual(['Done'])
    expect(Array.from(new Float64Array(outX))).toEqual([10, 20, 30])
  })

  it('change-values.worker posts Done and mutates Y in place', () => {
    const yBuf = bufferY([10, 20, 30])
    const posted = invokeChangeValues({
      bufferY: yBuf,
      indexes: [0, 2],
      operator: 'ADD',
      value: 5,
    })
    expect(posted).toEqual(['Done'])
    expect(Array.from(new Float64Array(yBuf))).toEqual([15, 20, 35])
  })

  it('change.worker posts the core output array', () => {
    const posted = invokeChange({
      bufferY: bufferY([10, 20, 21]),
      start: 1,
      end: 3,
      comparator: 'Greater than',
      value: 5,
    })
    expect(posted[0]).toEqual([1])
  })

  it('rate-of-change.worker posts the core output array', () => {
    const posted = invokeRateOfChange({
      bufferY: bufferY([10, 20]),
      start: 1,
      end: 2,
      comparator: 'Greater than',
      value: 0.5,
    })
    expect(posted[0]).toEqual([1])
  })

  it('find-gaps.worker posts the core output array', () => {
    const posted = invokeFindGaps({
      bufferX: bufferX([0, 1000, 6000]),
      start: 0,
      endInclusive: 2,
      threshold: 2000,
    })
    expect(posted[0]).toEqual([1, 2])
  })

  it('persistence.worker posts the core output array', () => {
    const posted = invokePersistence({
      bufferY: bufferY([1, 1, 2]),
      start: 0,
      end: 3,
    })
    expect(posted[0]).toEqual([0, 2, 1, 2, 1, 2])
  })

  it('fill-gaps.worker posts Done and writes fill points into the output', () => {
    const outX = emptyBufferX(4)
    const outY = emptyBufferY(4)
    const posted = invokeFillGaps({
      bufferX: bufferX([0, 10_000]),
      bufferY: bufferY([1, 2]),
      outputBufferX: outX,
      outputBufferY: outY,
      start: 0,
      end: 1,
      gapsSegment: [[0, 1]],
      startTarget: 0,
      fillDelta: 3000,
      interpolate: false,
      fillValue: -9999,
    })
    expect(posted).toEqual(['Done'])
    expect(Array.from(new Float64Array(outY))).toEqual([1, -9999, -9999, -9999])
  })

  it('interpolate.worker posts Done and mutates Y in place', () => {
    const yBuf = bufferY([0, 999, 20])
    const posted = invokeInterpolate({
      bufferX: bufferX([0, 1, 2]),
      bufferY: yBuf,
      groups: [{ indexes: [1], lowerIdx: 0, upperIdx: 2 }],
    })
    expect(posted).toEqual(['Done'])
    expect(new Float64Array(yBuf)[1]).toBe(10)
  })

  it('value-threshold.worker posts the core output array', () => {
    const posted = invokeValueThreshold({
      bufferY: bufferY([1, 5, 10]),
      start: 0,
      end: 3,
      ops: [2], // GT
      values: [4],
    })
    expect(posted[0]).toEqual([1, 2])
  })
})

describe('shift-datetimes.worker', () => {
  const payload = (x: number[], params: object) => {
    const outX = emptyBufferX(x.length)
    const outY = emptyBufferY(x.length)
    invokeShiftDatetimes({
      bufferX: bufferX(x),
      bufferY: bufferY(x.map((_, i) => i + 1)),
      outputBufferX: outX,
      outputBufferY: outY,
      indexes: x.map((_, i) => i),
      outStart: 0,
      ...params,
    })
    return [Array.from(new Float64Array(outX)), Array.from(new Float64Array(outY))]
  }

  it('shifts by a fixed span', () => {
    expect(
      payload([1_000_000, 3_000_000], { months: 0, deltaMs: 500_000, timeZone: 'UTC' })
    ).toEqual([
      [1_500_000, 3_500_000],
      [1, 2],
    ])
  })

  it('shifts by calendar months in the given zone', () => {
    const [x] = payload([Date.UTC(2026, 0, 15, 16)], {
      months: 6,
      deltaMs: 0,
      timeZone: 'America/Denver',
    })
    expect(x).toEqual([Date.UTC(2026, 6, 15, 15)])
  })
})

// ---------------------------------------------------------------------
// No-core workers — these still carry their algorithm inline so the
// test file is their only coverage. Keep behavioural assertions.
// ---------------------------------------------------------------------

describe('drift-correction.worker', () => {
  it('applies y_n = y_0 + value * ((x - startDatetime) / extent) for every job', () => {
    const x = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    const yBuf = bufferY(Array(x.length).fill(0))
    invokeDriftCorrection({
      bufferX: bufferX(x),
      bufferY: yBuf,
      jobs: [
        { chunkStart: 0, chunkEnd: 5, startDatetime: 0, value: 10, extent: 10 },
        { chunkStart: 5, chunkEnd: 10, startDatetime: 0, value: 10, extent: 10 },
      ],
    })
    const result = Array.from(new Float64Array(yBuf))
    expect(result.slice(0, 10)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    expect(result[10]).toBe(0)
  })
})
