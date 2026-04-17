/**
 * Direct unit tests for every `*.worker.ts` module.
 *
 * Each worker file registers its handler via `self.onmessage = ...` at module
 * evaluation time. We import each module once, capture its handler, then
 * exercise it synchronously by calling the handler with a mock message event
 * and redirecting `self.postMessage` into a local capture buffer.
 *
 * `self` resolves to the global `Window` under happy-dom; we overwrite its
 * `postMessage` per invocation so tests never race over a shared spy.
 */

import { describe, expect, it } from 'vitest';

type Handler = (e: { data: any }) => void;

async function loadWorker(importFn: () => Promise<unknown>) {
  (self as any).onmessage = null;
  (self as any).postMessage = () => {};
  await importFn();
  const handler = (self as any).onmessage as Handler;
  if (!handler) throw new Error('Worker module did not set self.onmessage');
  return (data: any): any[] => {
    const posted: any[] = [];
    (self as any).postMessage = (msg: any) => posted.push(msg);
    handler({ data });
    return posted;
  };
}

// Workers are imported sequentially; each overwrites self.onmessage, so grabbing
// it immediately is mandatory.
const invokeDelete = await loadWorker(() => import('../delete-data.worker'));
const invokeAdd = await loadWorker(() => import('../add-data.worker'));
const invokeChangeValues = await loadWorker(
  () => import('../change-values.worker'),
);
const invokeChange = await loadWorker(() => import('../change.worker'));
const invokeRateOfChange = await loadWorker(
  () => import('../rate-of-change.worker'),
);
const invokeFindGaps = await loadWorker(() => import('../find-gaps.worker'));
const invokePersistence = await loadWorker(
  () => import('../persistence.worker'),
);
const invokeFillGaps = await loadWorker(() => import('../fill-gaps.worker'));
const invokeInterpolate = await loadWorker(
  () => import('../interpolate.worker'),
);
const invokeValueThreshold = await loadWorker(
  () => import('../value-threshold.worker'),
);
const invokeShiftDatetimes = await loadWorker(
  () => import('../shift-datetimes.worker'),
);
const invokeDriftCorrection = await loadWorker(
  () => import('../drift-correction.worker'),
);

// ---------- Buffer helpers ----------

function bufferX(values: number[]): SharedArrayBuffer {
  const buf = new SharedArrayBuffer(values.length * Float64Array.BYTES_PER_ELEMENT);
  new Float64Array(buf).set(values);
  return buf;
}

function bufferY(values: number[]): SharedArrayBuffer {
  const buf = new SharedArrayBuffer(values.length * Float32Array.BYTES_PER_ELEMENT);
  new Float32Array(buf).set(values);
  return buf;
}

function emptyBufferX(length: number): SharedArrayBuffer {
  return new SharedArrayBuffer(length * Float64Array.BYTES_PER_ELEMENT);
}

function emptyBufferY(length: number): SharedArrayBuffer {
  return new SharedArrayBuffer(length * Float32Array.BYTES_PER_ELEMENT);
}

// =====================================================================

describe('delete-data.worker', () => {
  it('copies the segment to the output buffer, skipping deleteSegment indexes', () => {
    const x = [10, 20, 30, 40, 50];
    const y = [1, 2, 3, 4, 5];
    const outX = emptyBufferX(3);
    const outY = emptyBufferY(3);

    const posted = invokeDelete({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      start: 0,
      end: 4,
      deleteSegment: [1, 3],
      startTarget: 0,
    });

    expect(posted).toEqual(['Done']);
    expect(Array.from(new Float64Array(outX))).toEqual([10, 30, 50]);
    expect(Array.from(new Float32Array(outY))).toEqual([1, 3, 5]);
  });

  it('honors startTarget so multiple workers can share one output buffer', () => {
    const x = [10, 20, 30];
    const y = [1, 2, 3];
    const outX = emptyBufferX(5);
    const outY = emptyBufferY(5);

    invokeDelete({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      start: 0,
      end: 2,
      deleteSegment: [],
      startTarget: 2,
    });

    expect(Array.from(new Float64Array(outX))).toEqual([0, 0, 10, 20, 30]);
    expect(Array.from(new Float32Array(outY))).toEqual([0, 0, 1, 2, 3]);
  });
});

// =====================================================================

describe('add-data.worker', () => {
  it('merges originals with sorted insertions preserving datetime order', () => {
    const x = [10, 20, 30];
    const y = [1, 2, 3];
    const insertions: [number, number][] = [[15, 1.5], [25, 2.5]];
    const outX = emptyBufferX(5);
    const outY = emptyBufferY(5);

    invokeAdd({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      origStart: 0,
      origEnd: 3,
      insertions,
      outStart: 0,
    });

    expect(Array.from(new Float64Array(outX))).toEqual([10, 15, 20, 25, 30]);
    expect(Array.from(new Float32Array(outY))).toEqual([1, 1.5, 2, 2.5, 3]);
  });

  it('breaks datetime ties in favor of the original (matches findLastLessOrEqual)', () => {
    const x = [10, 20];
    const y = [1, 2];
    const outX = emptyBufferX(3);
    const outY = emptyBufferY(3);

    invokeAdd({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      origStart: 0,
      origEnd: 2,
      insertions: [[20, 99]],
      outStart: 0,
    });

    // Original (20, 2) must land before the inserted (20, 99)
    expect(Array.from(new Float64Array(outX))).toEqual([10, 20, 20]);
    expect(Array.from(new Float32Array(outY))).toEqual([1, 2, 99]);
  });

  it('appends insertions past the original end when no originals remain', () => {
    const x = [10];
    const y = [1];
    const outX = emptyBufferX(3);
    const outY = emptyBufferY(3);

    invokeAdd({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      origStart: 0,
      origEnd: 1,
      insertions: [[20, 2], [30, 3]],
      outStart: 0,
    });

    expect(Array.from(new Float64Array(outX))).toEqual([10, 20, 30]);
    expect(Array.from(new Float32Array(outY))).toEqual([1, 2, 3]);
  });
});

// =====================================================================

describe('change-values.worker', () => {
  const y = [10, 20, 30, 40];

  it('applies ADD / SUB / MULT / DIV / ASSIGN to the indexed elements', () => {
    for (const [operator, value, expected] of [
      ['ADD', 5, [15, 25, 30, 40]],
      ['SUB', 5, [5, 15, 30, 40]],
      ['MULT', 2, [20, 40, 30, 40]],
      ['DIV', 2, [5, 10, 30, 40]],
      ['ASSIGN', 99, [99, 99, 30, 40]],
    ] as const) {
      const yBuf = bufferY(y);
      invokeChangeValues({ bufferY: yBuf, indexes: [0, 1], operator, value });
      expect(Array.from(new Float32Array(yBuf))).toEqual(expected);
    }
  });

  it('is a no-op when the operator is unknown', () => {
    const yBuf = bufferY(y);
    invokeChangeValues({ bufferY: yBuf, indexes: [0, 1], operator: 'XYZ', value: 1 });
    expect(Array.from(new Float32Array(yBuf))).toEqual(y);
  });
});

// =====================================================================

describe('change.worker', () => {
  const y = [10, 20, 21, 10]; // Δ = 10, 1, -11

  it('selects indexes where the Δ matches each comparator', () => {
    for (const [comparator, value, expected] of [
      ['Less than', 0, [3]],
      ['Less than or equal to', 1, [2, 3]],
      ['Greater than', 1, [1]],
      ['Greater than or equal to', 10, [1]],
      ['Equal', 10, [1]],
    ] as const) {
      const posted = invokeChange({
        bufferY: bufferY(y),
        start: 1,
        end: y.length,
        comparator,
        value,
      });
      expect(posted[0]).toEqual(expected);
    }
  });
});

// =====================================================================

describe('rate-of-change.worker', () => {
  it('selects indexes where (curr-prev)/|prev| matches comparator', () => {
    // y = [10, 20, 15] → rates: (20-10)/10=1.0, (15-20)/20=-0.25
    const y = [10, 20, 15];
    const gt = invokeRateOfChange({
      bufferY: bufferY(y),
      start: 1,
      end: y.length,
      comparator: 'Greater than',
      value: 0.5,
    });
    expect(gt[0]).toEqual([1]);

    const lt = invokeRateOfChange({
      bufferY: bufferY(y),
      start: 1,
      end: y.length,
      comparator: 'Less than',
      value: 0,
    });
    expect(lt[0]).toEqual([2]);
  });
});

// =====================================================================

describe('find-gaps.worker', () => {
  it('emits [left, right] pairs where Δx exceeds threshold', () => {
    // x deltas: 1000, 5000, 1000 — threshold 2000 flags only the middle pair.
    const x = [0, 1000, 6000, 7000];
    const posted = invokeFindGaps({
      bufferX: bufferX(x),
      start: 0,
      endInclusive: 3,
      threshold: 2000,
    });
    expect(posted[0]).toEqual([1, 2]);
  });

  it('emits nothing when no delta exceeds the threshold', () => {
    const x = [0, 1000, 2000, 3000];
    const posted = invokeFindGaps({
      bufferX: bufferX(x),
      start: 0,
      endInclusive: 3,
      threshold: 10_000,
    });
    expect(posted[0]).toEqual([]);
  });
});

// =====================================================================

describe('persistence.worker', () => {
  it('emits (startIndex, length, value) triplets per run of equal y', () => {
    // y = [1, 1, 2, 3, 3, 3]
    const y = [1, 1, 2, 3, 3, 3];
    const posted = invokePersistence({
      bufferY: bufferY(y),
      start: 0,
      end: y.length,
    });
    expect(posted[0]).toEqual([0, 2, 1, 2, 1, 2, 3, 3, 3]);
  });

  it('returns an empty list when start >= end', () => {
    const posted = invokePersistence({
      bufferY: bufferY([1, 2, 3]),
      start: 2,
      end: 2,
    });
    expect(posted[0]).toEqual([]);
  });
});

// =====================================================================

describe('fill-gaps.worker', () => {
  it('inserts interpolated fill points inside detected gaps', () => {
    // x = [0, 1000, 11000], y = [0, 10, 110]. Gap between indexes 1 and 2.
    // fillDelta = 2000 → fills at 3000, 5000, 7000, 9000 (interpolated linearly from 10→110).
    const x = [0, 1000, 11000];
    const y = [0, 10, 110];
    const outX = emptyBufferX(3 + 4);
    const outY = emptyBufferY(3 + 4);

    invokeFillGaps({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      start: 0,
      end: 2,
      gapsSegment: [[1, 2]],
      startTarget: 0,
      fillDelta: 2000,
      interpolate: true,
      fillValue: -9999,
    });

    const resX = Array.from(new Float64Array(outX));
    const resY = Array.from(new Float32Array(outY));
    expect(resX).toEqual([0, 1000, 3000, 5000, 7000, 9000, 11000]);
    expect(resY).toEqual([0, 10, 30, 50, 70, 90, 110]);
  });

  it('uses fillValue when interpolate is false', () => {
    const x = [0, 10000];
    const y = [1, 2];
    const outX = emptyBufferX(4);
    const outY = emptyBufferY(4);

    invokeFillGaps({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      start: 0,
      end: 1,
      gapsSegment: [[0, 1]],
      startTarget: 0,
      fillDelta: 3000,
      interpolate: false,
      fillValue: -9999,
    });

    expect(Array.from(new Float32Array(outY))).toEqual([1, -9999, -9999, -9999]);
  });
});

// =====================================================================

describe('interpolate.worker', () => {
  it('linearly interpolates y at each index between the anchors', () => {
    // Uniform x [0..4], original y [0,10,999,999,40]. Interpolate indexes [2,3]
    // using lowerIdx=1 (y=10) and upperIdx=4 (y=40) → expected 20, 30.
    const x = [0, 1, 2, 3, 4];
    const y = [0, 10, 999, 999, 40];
    const yBuf = bufferY(y);
    invokeInterpolate({
      bufferX: bufferX(x),
      bufferY: yBuf,
      groups: [{ indexes: [2, 3], lowerIdx: 1, upperIdx: 4 }],
    });
    expect(+new Float32Array(yBuf)[2].toFixed(3)).toBe(20);
    expect(+new Float32Array(yBuf)[3].toFixed(3)).toBe(30);
  });

  it('collapses to the lower anchor when xSpan is zero', () => {
    const x = [5, 5, 5];
    const y = [1, 999, 3];
    const yBuf = bufferY(y);
    invokeInterpolate({
      bufferX: bufferX(x),
      bufferY: yBuf,
      groups: [{ indexes: [1], lowerIdx: 0, upperIdx: 2 }],
    });
    expect(new Float32Array(yBuf)[1]).toBe(1);
  });
});

// =====================================================================

describe('value-threshold.worker', () => {
  const y = [1, 5, 10, 15, 20];

  it('selects indexes where ANY opcode matches (short-circuit)', () => {
    // ops: LT(5), GT(18) → match indexes: 0 (<5) and 4 (>18)
    const posted = invokeValueThreshold({
      bufferY: bufferY(y),
      start: 0,
      end: y.length,
      ops: [0, 2],
      values: [5, 18],
    });
    expect(posted[0]).toEqual([0, 4]);
  });

  it('handles each opcode variant', () => {
    for (const [op, v, expected] of [
      [0, 10, [0, 1]],   // LT
      [1, 10, [0, 1, 2]], // LTE
      [2, 10, [3, 4]],   // GT
      [3, 10, [2, 3, 4]], // GTE
      [4, 10, [2]],      // E
      [99, 5, [1]],      // unknown → falls through to equality
    ] as const) {
      const posted = invokeValueThreshold({
        bufferY: bufferY(y),
        start: 0,
        end: y.length,
        ops: [op],
        values: [v],
      });
      expect(posted[0]).toEqual(expected);
    }
  });
});

// =====================================================================

describe('shift-datetimes.worker', () => {
  it('shifts by a precomputed deltaMs when unit is not month/year', () => {
    const x = [1_000_000, 2_000_000, 3_000_000];
    const y = [1, 2, 3];
    const outX = emptyBufferX(2);
    const outY = emptyBufferY(2);

    invokeShiftDatetimes({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      indexes: [0, 2],
      outStart: 0,
      amount: 1,
      isMonth: false,
      isYear: false,
      deltaMs: 500_000,
    });

    expect(Array.from(new Float64Array(outX))).toEqual([1_500_000, 3_500_000]);
    expect(Array.from(new Float32Array(outY))).toEqual([1, 3]);
  });

  it('shifts by calendar months when isMonth is true', () => {
    const base = Date.UTC(2024, 0, 15); // Jan 15 2024 UTC
    const x = [base];
    const y = [42];
    const outX = emptyBufferX(1);
    const outY = emptyBufferY(1);

    invokeShiftDatetimes({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      indexes: [0],
      outStart: 0,
      amount: 2,
      isMonth: true,
      isYear: false,
      deltaMs: 0,
    });

    const shifted = new Date(new Float64Array(outX)[0]);
    // setMonth uses local-time semantics; assert the delta in calendar months.
    const original = new Date(base);
    const months =
      (shifted.getFullYear() - original.getFullYear()) * 12 +
      (shifted.getMonth() - original.getMonth());
    expect(months).toBe(2);
    expect(new Float32Array(outY)[0]).toBe(42);
  });

  it('shifts by calendar years when isYear is true', () => {
    const base = Date.UTC(2024, 5, 10);
    const x = [base];
    const y = [7];
    const outX = emptyBufferX(1);
    const outY = emptyBufferY(1);

    invokeShiftDatetimes({
      bufferX: bufferX(x),
      bufferY: bufferY(y),
      outputBufferX: outX,
      outputBufferY: outY,
      indexes: [0],
      outStart: 0,
      amount: 3,
      isMonth: false,
      isYear: true,
      deltaMs: 0,
    });

    const shifted = new Date(new Float64Array(outX)[0]);
    const original = new Date(base);
    expect(shifted.getFullYear() - original.getFullYear()).toBe(3);
  });
});

// =====================================================================

describe('drift-correction.worker', () => {
  it('applies y_n = y_0 + value * ((x - startDatetime) / extent) for every job', () => {
    // x uniform grid, extent = 10, value = 10 → added offset = (i - 0).
    const x = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const y = Array(x.length).fill(0);
    const yBuf = bufferY(y);

    invokeDriftCorrection({
      bufferX: bufferX(x),
      bufferY: yBuf,
      jobs: [
        { chunkStart: 0, chunkEnd: 5, startDatetime: 0, value: 10, extent: 10 },
        { chunkStart: 5, chunkEnd: 10, startDatetime: 0, value: 10, extent: 10 },
      ],
    });

    const result = Array.from(new Float32Array(yBuf));
    expect(result.slice(0, 10)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    // index 10 is the range endpoint and is not touched (chunkEnd exclusive).
    expect(result[10]).toBe(0);
  });
});
