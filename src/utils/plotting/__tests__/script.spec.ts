import { beforeEach, describe, expect, it, vi } from 'vitest';

// Worker mocks must register before observation-record imports.
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

import { ObservationRecord } from '../observation-record';
import {
  applyScript,
  parseScript,
  serializeHistory,
  QC_SCRIPT_VERSION,
} from '../script';
import {
  EnumEditOperations,
  EnumFilterOperations,
  Operator,
  TimeUnit,
} from '@/types';

/** Build a uniform-grid dataset for tests. 15-min spacing, y = i. */
function makeRecord(size = 50): ObservationRecord {
  const startMs = Date.UTC(2024, 0, 1);
  const spacingMs = 15 * 60 * 1000;
  const datetimes = Array.from({ length: size }, (_, i) => startMs + i * spacingMs);
  const dataValues = Array.from({ length: size }, (_, i) => i);
  return new ObservationRecord({ datetimes, dataValues });
}

const SAMPLE_WINDOW = {
  startDate: '2024-01-01T00:00:00.000Z',
  endDate: '2024-01-02T00:00:00.000Z',
};

describe('serializeHistory', () => {
  let rec: ObservationRecord;
  beforeEach(async () => {
    rec = makeRecord(20);
    await rec.reload();
  });

  it('produces a v1 envelope with createdAt + window + operations', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    expect(script.version).toBe(QC_SCRIPT_VERSION);
    expect(typeof script.createdAt).toBe('string');
    expect(new Date(script.createdAt).toString()).not.toBe('Invalid Date');
    expect(script.window).toEqual(SAMPLE_WINDOW);
    expect(script.operations).toHaveLength(1);
    expect(script.operations[0].method).toBe(EnumFilterOperations.VALUE_THRESHOLD);
    expect(script.operations[0].args).toEqual([{ 'Greater than': 5 }]);
  });

  it('strips runtime-only fields (isLoading, duration, executionMode, selected, icon)', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    const op = script.operations[0] as Record<string, unknown>;
    expect(op.isLoading).toBeUndefined();
    expect(op.duration).toBeUndefined();
    expect(op.executionMode).toBeUndefined();
    expect(op.selected).toBeUndefined();
    expect(op.icon).toBeUndefined();
  });

  it('round-trips status: "failed" but omits the field for successful entries', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 0 });
    // Manually mark the entry as failed (the dispatch path sets this
    // on its own catch block; here we simulate post-hoc).
    rec.history[0].status = 'failed';
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].status).toBe('failed');

    rec.history[0].status = 'success';
    const ok = serializeHistory(rec, SAMPLE_WINDOW);
    expect(ok.operations[0].status).toBeUndefined();
  });
});

describe('parseScript', () => {
  it('accepts a well-formed v1 script', () => {
    const json = {
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        { method: 'VALUE_THRESHOLD', args: [{ 'Greater than': 5 }] },
      ],
    };
    const script = parseScript(json);
    expect(script.operations).toHaveLength(1);
    expect(script.window).toEqual(SAMPLE_WINDOW);
  });

  it('rejects an unknown version', () => {
    expect(() =>
      parseScript({ version: '2', createdAt: '', window: SAMPLE_WINDOW, operations: [] })
    ).toThrow(/Unsupported QC script version/);
  });

  it('rejects unknown method names', () => {
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [{ method: 'INVALID', args: [] }],
      })
    ).toThrow(/unknown method.*INVALID/);
  });

  it('rejects missing window', () => {
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        operations: [],
      })
    ).toThrow(/window/);
  });

  it('rejects non-array args', () => {
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [{ method: 'VALUE_THRESHOLD', args: 'not-an-array' }],
      })
    ).toThrow(/args.*array/);
  });
});

describe('applyScript — round-trip', () => {
  let rec: ObservationRecord;
  beforeEach(async () => {
    rec = makeRecord(20);
    await rec.reload();
  });

  it('round-trips an independent filter (VALUE_THRESHOLD)', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 10 });
    const before = rec.history.length;
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.applied).toBe(before);
    expect(report.failed).toEqual([]);
    expect(fresh.history.length).toBe(before);
    expect(fresh.history[0].method).toBe(EnumFilterOperations.VALUE_THRESHOLD);
    expect(fresh.history[0].args).toEqual([{ 'Greater than': 10 }]);
  });

  it('round-trips a SELECTION → DELETE_POINTS pair (selection-coupled)', async () => {
    const indices = [0, 1, 2, 5, 10];
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, indices],
      [EnumEditOperations.DELETE_POINTS],
    ]);
    const lenAfterDelete = rec.dataX.length;
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toEqual([]);
    expect(fresh.dataX.length).toBe(lenAfterDelete);
    // Replay restored the SELECTION + DELETE_POINTS pair.
    expect(fresh.history.map(h => h.method)).toEqual([
      EnumFilterOperations.SELECTION,
      EnumEditOperations.DELETE_POINTS,
    ]);
  });

  it('round-trips SELECTION → SHIFT_DATETIMES with non-index args preserved', async () => {
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [7, 8, 9]],
      [EnumEditOperations.SHIFT_DATETIMES, 1, TimeUnit.HOUR],
    ]);
    const xAfter = Array.from(rec.dataX);
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toEqual([]);
    expect(Array.from(fresh.dataX)).toEqual(xAfter);
    expect(fresh.history[1].args).toEqual([1, TimeUnit.HOUR]);
  });

  it('round-trips SELECTION → CHANGE_VALUES (consumes preceding selected at runtime)', async () => {
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [3, 4, 5]],
      [EnumEditOperations.CHANGE_VALUES, Operator.ASSIGN, 99],
    ]);
    const yAfter = Array.from(rec.dataY);
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toEqual([]);
    expect(Array.from(fresh.dataY)).toEqual(yAfter);
  });

  it('round-trips SELECTION → DRIFT_CORRECTION (consecutive-groups + value)', async () => {
    const sel: number[] = [];
    for (let i = 0; i <= 9; i++) sel.push(i);
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, sel],
      [EnumEditOperations.DRIFT_CORRECTION, 5],
    ]);
    const yAfter = Array.from(rec.dataY);
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toEqual([]);
    expect(Array.from(fresh.dataY)).toEqual(yAfter);
    expect(fresh.history[1].args).toEqual([5]);
  });

  it('round-trips ADD_POINTS (datetime-addressed, no selection coupling)', async () => {
    const ts = rec.dataX[5] + 1; // between two existing points
    await rec.dispatch(EnumEditOperations.ADD_POINTS, [[ts, 999]]);
    const lenAfter = rec.dataX.length;
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toEqual([]);
    expect(fresh.dataX.length).toBe(lenAfter);
  });

  it('round-trips a multi-step script and matches the source dataset bit-for-bit', async () => {
    await rec.dispatch([
      [EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 }],
      [EnumFilterOperations.SELECTION, [0, 1, 2]],
      [EnumEditOperations.DELETE_POINTS],
      [EnumFilterOperations.SELECTION, [4, 5]],
      [EnumEditOperations.CHANGE_VALUES, Operator.ASSIGN, -1],
    ]);
    const yAfter = Array.from(rec.dataY);
    const xAfter = Array.from(rec.dataX);
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toEqual([]);
    expect(Array.from(fresh.dataX)).toEqual(xAfter);
    expect(Array.from(fresh.dataY)).toEqual(yAfter);
  });

  it('clears history + redoStack before replay (in-place, preserving the array reference)', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    const script = serializeHistory(rec, SAMPLE_WINDOW);

    const fresh = makeRecord(20);
    await fresh.reload();
    // Pre-seed garbage state to confirm the loader resets it.
    await fresh.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Less than': 0 });
    await fresh.undo();
    expect(fresh.redoStack.length).toBeGreaterThan(0);

    const historyRef = fresh.history;
    const redoRef = fresh.redoStack;

    await applyScript(fresh, script);

    // Same array references — in-place clear, no re-assignment.
    expect(fresh.history).toBe(historyRef);
    expect(fresh.redoStack).toBe(redoRef);
    expect(fresh.redoStack.length).toBe(0);
    expect(fresh.history.length).toBe(1);
    expect(fresh.history[0].method).toBe(EnumFilterOperations.VALUE_THRESHOLD);
  });

  it('reports failures via ApplyScriptReport without aborting the rest of the script', async () => {
    // The failed op sits at index 0; the subsequent ADD_POINTS
    // (edit) breaks the filter chain so the cross-filter-replace
    // rule doesn't eat the failed entry, and a trailing CHANGE
    // (filter) lands as a new push (last item is the edit ADD,
    // not a filter, so neither same-method nor cross-filter replace
    // applies).
    const ts = makeRecord(20).dataX[5] + 1;
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        // VALUE_THRESHOLD with non-object args → handler reads
        // `Object.keys(null)` and throws.
        { method: 'VALUE_THRESHOLD', args: [null] },
        { method: 'ADD_POINTS', args: [[[ts, 99]]] },
        { method: 'CHANGE', args: ['Greater than', 0] },
      ],
    });

    const fresh = makeRecord(20);
    await fresh.reload();
    const report = await applyScript(fresh, script);

    expect(report.failed).toHaveLength(1);
    expect(report.failed[0].index).toBe(0);
    expect(report.failed[0].method).toBe('VALUE_THRESHOLD');
    expect(report.applied).toBe(2);
    // The failed entry stays in history with status: "failed" so
    // the UI can render its badge.
    const failedEntry = fresh.history.find(h => h.status === 'failed');
    expect(failedEntry).toBeDefined();
    expect(failedEntry?.method).toBe('VALUE_THRESHOLD');
  });
});
