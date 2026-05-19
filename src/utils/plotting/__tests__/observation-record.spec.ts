import { beforeEach, describe, expect, it, vi } from 'vitest';

// Worker mocks must be registered before `observation-record` is imported so
// the `?worker&inline` constructors resolve to the in-process shims.
vi.mock('../delete-data.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockDeleteDataWorker })));
vi.mock('../fill-gaps.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockFillGapsWorker })));
vi.mock('../interpolate.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockInterpolateWorker })));
vi.mock('../drift-correction.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockDriftCorrectionWorker })));
vi.mock('../add-data.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockAddDataWorker })));
vi.mock('../shift-datetimes.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockShiftDatetimesWorker })));
vi.mock('../find-gaps.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockFindGapsWorker })));
vi.mock('../persistence.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockPersistenceWorker })));
vi.mock('../change.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockChangeWorker })));
vi.mock('../rate-of-change.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockRateOfChangeWorker })));
vi.mock('../value-threshold.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockValueThresholdWorker })));
vi.mock('../change-values.worker?worker&inline', () => import('./workerMocks').then(m => ({ default: m.MockChangeValuesWorker })));

import { mockDatastream } from './mock';
import { ObservationRecord, INCREASE_AMOUNT } from '../observation-record';
import {
  EnumEditOperations,
  EnumFilterOperations,
  FilterOperation,
  Operator,
  TimeUnit,
} from '@/types';

/** Returns `amount` distinct sorted integers in [min, max]. */
function distinctSortedInts(amount: number, min: number, max: number): number[] {
  const rangeSize = max - min + 1;
  if (amount > rangeSize) {
    throw new Error(`Not enough distinct numbers between ${min} and ${max}`);
  }
  const result = new Set<number>();
  while (result.size < amount) {
    result.add(Math.floor(Math.random() * rangeSize) + min);
  }
  return [...result].sort((a, b) => a - b);
}

const mockRawData = {
  datetimes: mockDatastream.phenomenon_time.map((s) => new Date(s).getTime()),
  dataValues: mockDatastream.result,
};

/** Build a regular-grid dataset with y = y0 + i*step, 15-minute spacing. */
function buildUniformData(
  size: number,
  y0 = 0,
  step = 1,
  startMs = Date.UTC(2023, 0, 1),
  spacingMs = 15 * 60 * 1000,
) {
  const datetimes = new Array<number>(size);
  const dataValues = new Array<number>(size);
  for (let i = 0; i < size; i++) {
    datetimes[i] = startMs + i * spacingMs;
    dataValues[i] = y0 + i * step;
  }
  return { datetimes, dataValues, startMs, spacingMs };
}

describe('ObservationRecord', () => {
  describe('constructor & loadData', () => {
    it('loads raw data into typed arrays', async () => {
      const rec = new ObservationRecord(mockRawData);
      await rec.reload();

      expect(rec.dataX.length).toBe(mockRawData.datetimes.length);
      expect(rec.dataY.length).toBe(mockRawData.dataValues.length);
      expect(rec.dataX[0]).toBe(mockRawData.datetimes[0]);
      expect(rec.dataY[0]).toBeCloseTo(mockRawData.dataValues[0], 3);
      expect(rec.isLoading).toBe(false);
      expect(rec.loadingTime).not.toBeNull();
      expect(rec.history).toEqual([]);
    });

    it('returns early when dataArrays is falsy', async () => {
      const rec = new ObservationRecord(mockRawData);
      await rec.reload();
      await rec.loadData(undefined as any);
      // Raw data remains intact
      expect(rec.dataX.length).toBe(mockRawData.datetimes.length);
    });

    it('grows the shared buffer when raw data exceeds INCREASE_AMOUNT', async () => {
      const big = buildUniformData(INCREASE_AMOUNT + 1234);
      const rec = new ObservationRecord({
        datetimes: big.datetimes,
        dataValues: big.dataValues,
      });
      await rec.reload();

      expect(rec.dataX.length).toBe(big.datetimes.length);
      expect(rec.dataX[rec.dataX.length - 1]).toBe(big.datetimes[big.datetimes.length - 1]);
    });
  });

  describe('beginTime / endTime', () => {
    it('reflects the first and last datetime', async () => {
      const rec = new ObservationRecord(mockRawData);
      await rec.reload();
      expect(rec.beginTime?.getTime()).toBe(mockRawData.datetimes[0]);
      expect(rec.endTime?.getTime()).toBe(
        mockRawData.datetimes[mockRawData.datetimes.length - 1],
      );
    });

    it('returns null on an empty dataset', async () => {
      const rec = new ObservationRecord({ datetimes: [], dataValues: [] });
      await rec.reload();
      expect(rec.beginTime).toBeNull();
      expect(rec.endTime).toBeNull();
    });
  });

  describe('edit operations', () => {
    let rec: ObservationRecord;
    beforeEach(async () => {
      rec = new ObservationRecord(mockRawData);
      await rec.reload();
    });

    it('ADD_POINTS inserts points in sorted order and grows length', async () => {
      const toAdd = 100;
      const originalLength = rec.dataX.length;
      const randomDatetimes = distinctSortedInts(
        toAdd,
        mockRawData.datetimes[0],
        mockRawData.datetimes[mockRawData.datetimes.length - 1],
      );
      const dataPointsToAdd: [number, number][] = randomDatetimes.map((dt) => [
        dt,
        +(Math.random() * 10).toFixed(3),
      ]);

      await rec.dispatch(EnumEditOperations.ADD_POINTS, dataPointsToAdd);

      expect(rec.dataX.length).toBe(originalLength + toAdd);
      // Datetimes remain sorted ascending
      for (let i = 1; i < rec.dataX.length; i++) {
        expect(rec.dataX[i]).toBeGreaterThanOrEqual(rec.dataX[i - 1]);
      }
      expect(rec.history[rec.history.length - 1].method).toBe(
        EnumEditOperations.ADD_POINTS,
      );
    });

    it('ADD_POINTS is a no-op when insertions are empty', async () => {
      const originalLength = rec.dataX.length;
      await rec.dispatch(EnumEditOperations.ADD_POINTS, []);
      expect(rec.dataX.length).toBe(originalLength);
    });

    it('DELETE_POINTS removes selected indexes and shrinks length', async () => {
      const toDelete = 100;
      const originalLength = rec.dataX.length;
      const indexes = distinctSortedInts(toDelete, 0, originalLength - 1);
      const keptX = Array.from(rec.dataX).filter((_, i) => !indexes.includes(i));

      // Seed the selection then delete (the dispatch wrapper reads
      // indices off the preceding SELECTION).
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, indexes],
        [EnumEditOperations.DELETE_POINTS],
      ]);

      expect(rec.dataX.length).toBe(originalLength - toDelete);
      expect(rec.dataX[0]).toBe(keptX[0]);
      expect(rec.dataX[rec.dataX.length - 1]).toBe(keptX[keptX.length - 1]);
    });

    it('CHANGE_VALUES applies operator to the prior SELECTION indexes', async () => {
      const indexes = distinctSortedInts(25, 0, rec.dataX.length - 1);
      const originalY = indexes.map((i) => rec.dataY[i]);

      // Seed the selection first, then change values on that selection.
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, indexes],
        [EnumEditOperations.CHANGE_VALUES, Operator.ADD, 2],
      ]);

      const after = indexes.map((i) => +rec.dataY[i].toFixed(3));
      const expected = originalY.map((v) => +(v + 2).toFixed(3));
      expect(after).toEqual(expected);
    });

    it('CHANGE_VALUES supports SUB / MULT / DIV / ASSIGN operators', async () => {
      const idx = [5, 10, 15];
      const base = idx.map((i) => rec.dataY[i]);

      await rec.dispatch([
        [EnumFilterOperations.SELECTION, idx],
        [EnumEditOperations.CHANGE_VALUES, Operator.MULT, 2],
      ]);
      idx.forEach((i, k) =>
        expect(+rec.dataY[i].toFixed(3)).toBe(+(base[k] * 2).toFixed(3)),
      );

      await rec.reload();
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, idx],
        [EnumEditOperations.CHANGE_VALUES, Operator.SUB, 1.5],
      ]);
      idx.forEach((i, k) =>
        expect(+rec.dataY[i].toFixed(3)).toBe(+(base[k] - 1.5).toFixed(3)),
      );

      await rec.reload();
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, idx],
        [EnumEditOperations.CHANGE_VALUES, Operator.DIV, 2],
      ]);
      idx.forEach((i, k) =>
        expect(+rec.dataY[i].toFixed(3)).toBe(+(base[k] / 2).toFixed(3)),
      );

      await rec.reload();
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, idx],
        [EnumEditOperations.CHANGE_VALUES, Operator.ASSIGN, 42],
      ]);
      idx.forEach((i) => expect(rec.dataY[i]).toBe(42));
    });

    it('CHANGE_VALUES returns early when no selection is present', async () => {
      const beforeY = Array.from(rec.dataY);
      await rec.dispatch(EnumEditOperations.CHANGE_VALUES, Operator.ADD, 5);
      expect(Array.from(rec.dataY)).toEqual(beforeY);
    });

    it('INTERPOLATE linearly fills y between anchors', async () => {
      const uniform = buildUniformData(20, 0, 10); // y = 0, 10, 20, ..., 190
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();

      // Overwrite the middle span so we can check interpolation recovers a line
      local.dataY[5] = 999;
      local.dataY[6] = 999;
      local.dataY[7] = 999;

      await local.dispatch([
        [EnumFilterOperations.SELECTION, [5, 6, 7]],
        [EnumEditOperations.INTERPOLATE],
      ]);

      // Anchors are indexes 4 (y=40) and 8 (y=80). Interpolation at uniformly-spaced x
      // gives y = 50, 60, 70.
      expect(+local.dataY[5].toFixed(3)).toBe(50);
      expect(+local.dataY[6].toFixed(3)).toBe(60);
      expect(+local.dataY[7].toFixed(3)).toBe(70);
    });

    it('INTERPOLATE is a no-op when no preceding selection', async () => {
      const uniform = buildUniformData(10, 0, 10);
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();
      const before = Array.from(local.dataY);
      // No SELECTION dispatched first → wrapper bails.
      await local.dispatch(EnumEditOperations.INTERPOLATE);
      expect(Array.from(local.dataY)).toEqual(before);
    });

    it('DRIFT_CORRECTION applies linear drift over [start, end]', async () => {
      const uniform = buildUniformData(10, 0, 10); // y = 0..90
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();

      // Drift value = 18 over indexes [0, 9] (exclusive end) →
      // y += 18 * (x - x0) / (x9 - x0). Worker loops i < end, so y[9] is untouched.
      const baseY = Array.from(local.dataY);
      // Build a selection covering [0..9] consecutively so the
      // wrapper's `_getConsecutiveGroups` collapses it back into one
      // [start, end, value] range.
      const sel: number[] = [];
      for (let i = 0; i <= 9; i++) sel.push(i);
      await local.dispatch([
        [EnumFilterOperations.SELECTION, sel],
        [EnumEditOperations.DRIFT_CORRECTION, 18],
      ]);

      expect(+local.dataY[0].toFixed(3)).toBe(+baseY[0].toFixed(3));
      expect(+local.dataY[9].toFixed(3)).toBe(+baseY[9].toFixed(3));
      expect(+local.dataY[5].toFixed(3)).toBe(+(baseY[5] + 10).toFixed(3));
      expect(+local.dataY[8].toFixed(3)).toBe(+(baseY[8] + 16).toFixed(3));
    });

    it('DRIFT_CORRECTION is a no-op for empty or degenerate ranges', async () => {
      const uniform = buildUniformData(10, 0, 10);
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();
      const before = Array.from(local.dataY);

      // No preceding SELECTION → wrapper bails.
      await local.dispatch(EnumEditOperations.DRIFT_CORRECTION, 10);
      expect(Array.from(local.dataY)).toEqual(before);

      // Single-point selection → group is [5], end <= start → internal handler skips.
      await local.dispatch([
        [EnumFilterOperations.SELECTION, [5]],
        [EnumEditOperations.DRIFT_CORRECTION, 10],
      ]);
      expect(Array.from(local.dataY)).toEqual(before);
    });

    it('SHIFT_DATETIMES offsets selected points by a TimeUnit amount', async () => {
      const uniform = buildUniformData(10, 0, 10);
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();

      // Shift the last 3 points by +1 hour. Since grid is 15 min, this moves them
      // past later (nonexistent) positions but doesn't change count.
      const originalLen = local.dataX.length;
      await local.dispatch([
        [EnumFilterOperations.SELECTION, [7, 8, 9]],
        [EnumEditOperations.SHIFT_DATETIMES, 1, TimeUnit.HOUR],
      ]);
      expect(local.dataX.length).toBe(originalLen);
      // Datetimes still sorted
      for (let i = 1; i < local.dataX.length; i++) {
        expect(local.dataX[i]).toBeGreaterThanOrEqual(local.dataX[i - 1]);
      }
    });

    it('SHIFT_DATETIMES is a no-op when no preceding selection', async () => {
      const uniform = buildUniformData(5, 0, 10);
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();
      const before = Array.from(local.dataX);
      // No SELECTION dispatched first → wrapper bails.
      await local.dispatch(EnumEditOperations.SHIFT_DATETIMES, 1, TimeUnit.HOUR);
      expect(Array.from(local.dataX)).toEqual(before);
    });

    it('FILL_GAPS inserts points in detected gaps (with interpolation)', async () => {
      // Build a dataset with a single 4-hour gap in an otherwise 15-min grid.
      const spacingMs = 15 * 60 * 1000;
      const startMs = Date.UTC(2023, 0, 1);
      const datetimes: number[] = [];
      const dataValues: number[] = [];
      for (let i = 0; i < 5; i++) {
        datetimes.push(startMs + i * spacingMs);
        dataValues.push(i * 10);
      }
      // Gap: jump ~4 hours forward
      const gapStart = datetimes[datetimes.length - 1];
      const resumeAt = gapStart + 4 * 60 * 60 * 1000; // +4h
      datetimes.push(resumeAt);
      dataValues.push(1000);
      for (let i = 1; i < 5; i++) {
        datetimes.push(resumeAt + i * spacingMs);
        dataValues.push(1000 + i * 10);
      }

      const local = new ObservationRecord({ datetimes, dataValues });
      await local.reload();
      const originalLen = local.dataX.length;

      // Gap threshold: > 30 minutes. Fill at 1 hour intervals, interpolate values.
      await local.dispatch(
        EnumEditOperations.FILL_GAPS,
        [30, TimeUnit.MINUTE],
        [1, TimeUnit.HOUR],
        true,
        -9999,
      );

      expect(local.dataX.length).toBeGreaterThan(originalLen);
      // Monotonic datetimes after fill
      for (let i = 1; i < local.dataX.length; i++) {
        expect(local.dataX[i]).toBeGreaterThanOrEqual(local.dataX[i - 1]);
      }
    });

    it('FILL_GAPS is a no-op when no gap exceeds the threshold', async () => {
      const uniform = buildUniformData(20, 0, 10); // 15-min spacing
      const local = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await local.reload();
      const before = local.dataX.length;
      await local.dispatch(
        EnumEditOperations.FILL_GAPS,
        [1, TimeUnit.HOUR],
        [15, TimeUnit.MINUTE],
        false,
        -9999,
      );
      expect(local.dataX.length).toBe(before);
    });
  });

  describe('filter operations', () => {
    let rec: ObservationRecord;
    beforeEach(async () => {
      const uniform = buildUniformData(20, 0, 10); // y = 0..190
      rec = new ObservationRecord({
        datetimes: uniform.datetimes,
        dataValues: uniform.dataValues,
      });
      await rec.reload();
    });

    it('VALUE_THRESHOLD selects points matching the filter map', async () => {
      const selection = await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, {
        [FilterOperation.GTE]: 100,
      });
      expect(selection).toEqual([10, 11, 12, 13, 14, 15, 16, 17, 18, 19]);
    });

    it('VALUE_THRESHOLD returns [] for an empty filter map', async () => {
      const selection = await rec.dispatch(
        EnumFilterOperations.VALUE_THRESHOLD,
        {},
      );
      expect(selection).toEqual([]);
    });

    it('CHANGE selects points whose Δy matches the comparator', async () => {
      // Uniform step = 10 → every Δ equals 10.
      const selection = await rec.dispatch(
        EnumFilterOperations.CHANGE,
        FilterOperation.GTE,
        10,
      );
      expect(selection.length).toBe(rec.dataY.length - 1);
      expect(selection[0]).toBe(1);
    });

    it('CHANGE returns [] for datasets shorter than 2', async () => {
      const tiny = new ObservationRecord({ datetimes: [0], dataValues: [0] });
      await tiny.reload();
      const selection = await tiny.dispatch(
        EnumFilterOperations.CHANGE,
        FilterOperation.GT,
        0,
      );
      expect(selection).toEqual([]);
    });

    it('RATE_OF_CHANGE selects points whose relative rate matches', async () => {
      // y = 10, 20, 30, ... → rate at i=1 is (20-10)/|10| = 1.0
      const selection = await rec.dispatch(
        EnumFilterOperations.RATE_OF_CHANGE,
        FilterOperation.GT,
        0.5,
      );
      expect(selection).toContain(1);
    });

    it('FIND_GAPS returns pairs of indexes with large delta', async () => {
      const spacingMs = 15 * 60 * 1000;
      const startMs = Date.UTC(2023, 0, 1);
      const datetimes = [
        startMs,
        startMs + spacingMs,
        startMs + spacingMs + 4 * 60 * 60 * 1000, // gap
        startMs + spacingMs + 4 * 60 * 60 * 1000 + spacingMs,
      ];
      const dataValues = [0, 1, 2, 3];
      const local = new ObservationRecord({ datetimes, dataValues });
      await local.reload();

      const selection = await local.dispatch(
        EnumFilterOperations.FIND_GAPS,
        30,
        TimeUnit.MINUTE,
      );
      expect(selection.sort((a, b) => a - b)).toEqual([1, 2]);
    });

    it('FIND_GAPS returns [] when start >= end', async () => {
      const empty = new ObservationRecord({ datetimes: [], dataValues: [] });
      await empty.reload();
      const selection = await empty.dispatch(
        EnumFilterOperations.FIND_GAPS,
        1,
        TimeUnit.HOUR,
      );
      expect(selection).toEqual([]);
    });

    it('PERSISTENCE selects runs of equal consecutive y of length >= times', async () => {
      const datetimes = Array.from({ length: 10 }, (_, i) => i * 1000);
      const dataValues = [1, 1, 1, 2, 2, 3, 3, 3, 3, 4];
      const local = new ObservationRecord({ datetimes, dataValues });
      await local.reload();

      const selection = await local.dispatch(EnumFilterOperations.PERSISTENCE, 3);
      // Runs of length >= 3: [0,1,2] (value 1) and [5,6,7,8] (value 3)
      expect(selection.sort((a, b) => a - b)).toEqual([0, 1, 2, 5, 6, 7, 8]);
    });

    it('PERSISTENCE returns [] on empty range', async () => {
      const empty = new ObservationRecord({ datetimes: [], dataValues: [] });
      await empty.reload();
      const selection = await empty.dispatch(EnumFilterOperations.PERSISTENCE, 2);
      expect(selection).toEqual([]);
    });

    it('FIND_GAPS respects an optional [from, to] range', async () => {
      const spacingMs = 15 * 60 * 1000;
      const startMs = Date.UTC(2023, 0, 1);
      // Two gaps: one outside the window (between 1 and 2), one inside
      // (between 4 and 5). With the range clipped to [2, 5], the
      // pre-window gap should be invisible to the scan.
      const datetimes = [
        startMs,
        startMs + spacingMs,
        startMs + spacingMs + 4 * 60 * 60 * 1000,                     // pre-window gap
        startMs + spacingMs + 4 * 60 * 60 * 1000 + spacingMs,
        startMs + spacingMs + 4 * 60 * 60 * 1000 + 2 * spacingMs,
        startMs + spacingMs + 4 * 60 * 60 * 1000 + 2 * spacingMs + 4 * 60 * 60 * 1000, // in-window gap
        startMs + spacingMs + 4 * 60 * 60 * 1000 + 2 * spacingMs + 4 * 60 * 60 * 1000 + spacingMs,
      ];
      const dataValues = datetimes.map((_, i) => i);
      const local = new ObservationRecord({ datetimes, dataValues });
      await local.reload();

      const fromTs = datetimes[2];
      const toTs = datetimes[6];
      const selection = await local.dispatch(
        EnumFilterOperations.FIND_GAPS,
        30,
        TimeUnit.MINUTE,
        [fromTs, toTs],
      );
      // The pre-window gap (indices 1-2) is excluded; only the
      // in-window gap (indices 4-5) survives.
      expect(selection.sort((a, b) => a - b)).toEqual([4, 5]);
    });

    it('PERSISTENCE respects an optional [from, to] range', async () => {
      const spacingMs = 15 * 60 * 1000;
      const startMs = Date.UTC(2023, 0, 1);
      const datetimes = Array.from({ length: 10 }, (_, i) => startMs + i * spacingMs);
      // Two plateaus: one in [0..2] (value 1), one in [5..8] (value 3).
      // Range clipped to [3..9] excludes the first plateau entirely.
      const dataValues = [1, 1, 1, 2, 2, 3, 3, 3, 3, 4];
      const local = new ObservationRecord({ datetimes, dataValues });
      await local.reload();

      const fromTs = datetimes[3];
      const toTs = datetimes[9];
      const selection = await local.dispatch(
        EnumFilterOperations.PERSISTENCE,
        3,
        [fromTs, toTs],
      );
      // First plateau falls outside the window; only the second
      // (indices 5..8) qualifies.
      expect(selection.sort((a, b) => a - b)).toEqual([5, 6, 7, 8]);
    });

    it('VALUE_THRESHOLD respects an optional [from, to] range', async () => {
      // Fixture from `buildUniformData(20, 0, 10)`: 20 points,
      // 15-minute spacing starting at `Date.UTC(2023, 0, 1)`.
      // y = 0, 10, ..., 190.
      const startMs = Date.UTC(2023, 0, 1);
      const spacingMs = 15 * 60 * 1000;
      const fromTs = startMs + 5 * spacingMs; // index 5
      const toTs = startMs + 10 * spacingMs; // index 10
      // y >= 80 selects 8..19; intersect with the window → [8, 9, 10].
      const selection = await rec.dispatch(
        EnumFilterOperations.VALUE_THRESHOLD,
        { [FilterOperation.GTE]: 80 },
        [fromTs, toTs],
      );
      expect(selection.sort((a, b) => a - b)).toEqual([8, 9, 10]);
    });

    it('CHANGE respects an optional [from, to] range', async () => {
      const startMs = Date.UTC(2023, 0, 1);
      const spacingMs = 15 * 60 * 1000;
      const fromTs = startMs + 5 * spacingMs;
      const toTs = startMs + 10 * spacingMs;
      // Δ between every adjacent pair is 10 (uniform step). The
      // kernel reads `Y[i-1]`, so the scan starts at the first
      // index >= start within the window — indices 5..10. Every
      // sample matches `>= 10`.
      const selection = await rec.dispatch(
        EnumFilterOperations.CHANGE,
        FilterOperation.GTE,
        10,
        [fromTs, toTs],
      );
      expect(selection.sort((a, b) => a - b)).toEqual([5, 6, 7, 8, 9, 10]);
    });

    it('RATE_OF_CHANGE respects an optional [from, to] range', async () => {
      const startMs = Date.UTC(2023, 0, 1);
      const spacingMs = 15 * 60 * 1000;
      const fromTs = startMs + 5 * spacingMs;
      const toTs = startMs + 10 * spacingMs;
      // Same fixture (y = i*10) → relative rate at each i is
      // (10) / |Y[i-1]|. All > 0; bounding the scan to indices
      // 5..10 returns those indices.
      const selection = await rec.dispatch(
        EnumFilterOperations.RATE_OF_CHANGE,
        FilterOperation.GT,
        0,
        [fromTs, toTs],
      );
      expect(selection.sort((a, b) => a - b)).toEqual([5, 6, 7, 8, 9, 10]);
    });

    it('range argument with bounds beyond data extent yields []', async () => {
      const farFuture = Date.UTC(2099, 0, 1);
      const selection = await rec.dispatch(
        EnumFilterOperations.VALUE_THRESHOLD,
        { [FilterOperation.GTE]: 0 },
        [farFuture, farFuture + 1000],
      );
      expect(selection).toEqual([]);
    });

    it('SELECTION echoes input and pops history when cleared', async () => {
      const selection = await rec.dispatch(
        EnumFilterOperations.SELECTION,
        [1, 2, 3],
      );
      expect(selection).toEqual([1, 2, 3]);
      const historyLenWithSelection = rec.history.length;

      // Clearing selection removes the history entry
      await rec.dispatch(EnumFilterOperations.SELECTION, []);
      expect(rec.history.length).toBe(historyLenWithSelection - 1);
    });

    it('dispatchFilter replaces the trailing filter entry rather than stacking', async () => {
      await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, {
        [FilterOperation.GTE]: 100,
      });
      const lenAfterFirst = rec.history.length;
      await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, {
        [FilterOperation.GTE]: 150,
      });
      expect(rec.history.length).toBe(lenAfterFirst);
      expect(rec.history[rec.history.length - 1].method).toBe(
        EnumFilterOperations.VALUE_THRESHOLD,
      );
    });
  });

  describe('history management', () => {
    let rec: ObservationRecord;
    beforeEach(async () => {
      rec = new ObservationRecord(mockRawData);
      await rec.reload();
    });

    it('reload() restores the raw dataset and clears history', async () => {
      const indexes = distinctSortedInts(10, 0, rec.dataX.length - 1);
      const originalLen = rec.dataX.length;
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, indexes],
        [EnumEditOperations.DELETE_POINTS],
      ]);
      expect(rec.dataX.length).toBe(originalLen - 10);

      await rec.reload();
      expect(rec.dataX.length).toBe(originalLen);
      expect(rec.history).toEqual([]);
    });

    it('reloadHistory replays entries up to a given index', async () => {
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, [0, 1]],
        [EnumEditOperations.DELETE_POINTS],
        [EnumFilterOperations.SELECTION, [0]],
        [EnumEditOperations.DELETE_POINTS],
      ]);
      const lenAfterTwo = rec.dataX.length;

      // Replay only up through the first SELECTION + DELETE pair (entries 0 + 1).
      await rec.reloadHistory(1);
      expect(rec.dataX.length).toBe(mockRawData.datetimes.length - 2);
      expect(rec.dataX.length).toBeGreaterThan(lenAfterTwo);
    });

    it('removeHistoryItem replays history without the removed entry', async () => {
      const originalLen = rec.dataX.length;
      // Two SELECTION + DELETE pairs (entries 0..3).
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, [0, 1, 2]],
        [EnumEditOperations.DELETE_POINTS],
        [EnumFilterOperations.SELECTION, [0]],
        [EnumEditOperations.DELETE_POINTS],
      ]);
      expect(rec.dataX.length).toBe(originalLen - 4);

      // Remove the first SELECTION entry (index 0). Replay drops
      // the now-orphaned first DELETE_POINTS (no preceding SELECTION
      // → wrapper bails) and runs the second SELECTION + DELETE
      // pair, which removes one point.
      await rec.removeHistoryItem(0);
      expect(rec.dataX.length).toBe(originalLen - 1);
    });
  });

  describe('dispatch', () => {
    it('runs a batched sequence and returns the last response', async () => {
      const rec = new ObservationRecord(mockRawData);
      await rec.reload();
      const result = await rec.dispatch([
        [EnumFilterOperations.SELECTION, [1, 2, 3]],
        [EnumEditOperations.CHANGE_VALUES, Operator.ADD, 1],
      ]);
      // CHANGE_VALUES returns [] by design; the test exercises the batched path.
      expect(Array.isArray(result)).toBe(true);
    });

    it('swallows errors thrown inside an action without aborting', async () => {
      const rec = new ObservationRecord(mockRawData);
      await rec.reload();
      // Unknown action strings fall through; dispatch should not throw.
      await expect(
        rec.dispatch('NOT_A_REAL_OP' as any, []),
      ).resolves.toBeDefined();
    });
  });
});
