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

  it('round-trips the per-operation timestamp into QcScriptOperation.timestamp', async () => {
    const before = Date.now();
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    const after = Date.now();
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    const ts = script.operations[0].timestamp;
    expect(typeof ts).toBe('number');
    // Dispatch stamps Date.now() at push time — must land inside the
    // [before, after] window we captured around the dispatch call.
    expect(ts).toBeGreaterThanOrEqual(before);
    expect(ts).toBeLessThanOrEqual(after);
  });

  it('omits timestamp from the script when the history entry has no timestamp', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    // Simulate an entry constructed outside the dispatch path (no
    // stamp). serializeHistory must not invent one.
    delete rec.history[0].timestamp;
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].timestamp).toBeUndefined();
  });

  it('skips non-finite timestamp values during serialize', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    rec.history[0].timestamp = NaN;
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].timestamp).toBeUndefined();
  });

  it('serializes args as an empty array when the history entry has no args', async () => {
    // The `h.args ? [...h.args] : []` ternary's else branch only
    // fires when args is undefined / falsy. Construct an entry by
    // hand so the dispatch path doesn't auto-fill `args = []`.
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    delete rec.history[0].args;
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].args).toEqual([]);
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

  it('rejects a non-object root (null, primitive, undefined)', () => {
    expect(() => parseScript(null)).toThrow(/QC script must be a JSON object/);
    expect(() => parseScript(undefined)).toThrow(/QC script must be a JSON object/);
    expect(() => parseScript('not-a-script')).toThrow(/QC script must be a JSON object/);
    expect(() => parseScript(42)).toThrow(/QC script must be a JSON object/);
  });

  it('rejects a missing or non-string `createdAt`', () => {
    expect(() =>
      parseScript({ version: '1', window: SAMPLE_WINDOW, operations: [] })
    ).toThrow(/missing `createdAt`/);
    expect(() =>
      parseScript({ version: '1', createdAt: 12345, window: SAMPLE_WINDOW, operations: [] })
    ).toThrow(/missing `createdAt`/);
  });

  it('rejects window entries whose start/end dates are not ISO-8601 strings', () => {
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: { startDate: 12345, endDate: '2024-01-02T00:00:00.000Z' },
        operations: [],
      })
    ).toThrow(/ISO-8601 strings/);
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: { startDate: '2024-01-01T00:00:00.000Z', endDate: null },
        operations: [],
      })
    ).toThrow(/ISO-8601 strings/);
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

  it('rejects a top-level `operations` field that is not an array', () => {
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: 'oops',
      })
    ).toThrow(/operations.*array/);
  });

  it('rejects per-op entries that are not objects (null, primitive)', () => {
    const bad = (entry: unknown) => () =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [entry],
      });
    expect(bad(null)).toThrow(/Operation 0 must be an object/);
    expect(bad('VALUE_THRESHOLD')).toThrow(/Operation 0 must be an object/);
    expect(bad(42)).toThrow(/Operation 0 must be an object/);
  });

  it('rejects per-op entries missing a string `method`', () => {
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [{ args: [] }],
      })
    ).toThrow(/missing string `method`/);
    expect(() =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [{ method: 42, args: [] }],
      })
    ).toThrow(/missing string `method`/);
  });

  it('accepts an optional finite-number timestamp on a per-operation entry', () => {
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        { method: 'VALUE_THRESHOLD', args: [{ 'Greater than': 5 }], timestamp: 1745597000000 },
      ],
    });
    expect(script.operations[0].timestamp).toBe(1745597000000);
  });

  it('tolerates pre-v1.1 operations without a timestamp (backward-compatible)', () => {
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [{ method: 'VALUE_THRESHOLD', args: [] }],
    });
    expect(script.operations[0].timestamp).toBeUndefined();
  });

  it('rejects a non-finite timestamp (NaN, Infinity, wrong type)', () => {
    const bad = (timestamp: unknown) => () =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [{ method: 'VALUE_THRESHOLD', args: [], timestamp }],
      });
    expect(bad('1745597000000')).toThrow(/timestamp.*finite/);
    expect(bad(NaN)).toThrow(/timestamp.*finite/);
    expect(bad(Infinity)).toThrow(/timestamp.*finite/);
  });

  it('round-trips an operation marked status: "failed" through parseScript', () => {
    // Drives the `o.status === "failed"` branch of parseScript so
    // the field copies onto the resulting QcScriptOperation. The
    // serializeHistory equivalent already covers the other half of
    // the round-trip.
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        { method: 'VALUE_THRESHOLD', args: [], status: 'failed' },
      ],
    });
    expect(script.operations[0].status).toBe('failed');
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

  it('replay re-stamps HistoryItem.timestamp with Date.now() and ignores the persisted value', async () => {
    // Persisted timestamp is intentionally far in the past — if the
    // loader forwarded it, the replayed entry would carry that
    // antique stamp. The contract is that it does NOT: dispatch
    // stamps a fresh `Date.now()` for the new execution, leaving the
    // saved value untouched in the script for later audit.
    const PERSISTED = Date.UTC(2020, 0, 1); // 2020-01-01
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        { method: 'VALUE_THRESHOLD', args: [{ 'Greater than': 5 }], timestamp: PERSISTED },
      ],
    });

    const fresh = makeRecord(20);
    await fresh.reload();
    const before = Date.now();
    await applyScript(fresh, script);
    const after = Date.now();

    const ts = fresh.history[0].timestamp;
    expect(typeof ts).toBe('number');
    expect(ts).not.toBe(PERSISTED);
    expect(ts).toBeGreaterThanOrEqual(before);
    expect(ts).toBeLessThanOrEqual(after);
    // The original script object is unchanged — the saved value
    // survives for later audit even though replay overwrote the
    // in-memory field.
    expect(script.operations[0].timestamp).toBe(PERSISTED);
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

  it('catches Error throws from dispatch and surfaces .message in the report', async () => {
    // Covers the `e instanceof Error ? e.message : ...` true branch
    // of applyScript's defensive catch.
    const stub = {
      history: [],
      redoStack: [],
      reload: async () => { },
      dispatch: async () => { throw new Error('boom-with-stack'); },
    } as unknown as ObservationRecord;

    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [{ method: 'VALUE_THRESHOLD', args: [] }],
    });
    const report = await applyScript(stub, script);
    expect(report.failed).toHaveLength(1);
    expect(report.failed[0].error).toBe('boom-with-stack');
  });

  it('catches non-Error throws from dispatch and stringifies the value into the report', async () => {
    // `dispatchAction` / `dispatchFilter` normally swallow handler
    // errors themselves, but the catch in `applyScript` is defensive
    // and handles a bare throw too. Stub `record.dispatch` so it
    // throws a plain string — the catch path must stringify it
    // (line 220's `e instanceof Error ? e.message : String(e)`
    // ternary) and record it in `report.failed[].error` without
    // aborting the surrounding loop.
    const stub = {
      history: [],
      redoStack: [],
      reload: async () => { },
      dispatch: async () => { throw 'plain-string-failure'; },
    } as unknown as ObservationRecord;

    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [{ method: 'VALUE_THRESHOLD', args: [] }],
    });
    const report = await applyScript(stub, script);
    expect(report.applied).toBe(0);
    expect(report.failed).toHaveLength(1);
    expect(report.failed[0].error).toBe('plain-string-failure');
  });
});
