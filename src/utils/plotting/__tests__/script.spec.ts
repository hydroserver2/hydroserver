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

  it('round-trips execution.status into the persisted op, omitting it for successful entries', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 0 });
    rec.history[0].execution.status = 'failed';
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].execution?.status).toBe('failed');

    rec.history[0].execution.status = 'success';
    const ok = serializeHistory(rec, SAMPLE_WINDOW);
    expect(ok.operations[0].execution?.status).toBe('success');
  });

  it('round-trips execution.startedAt verbatim into the persisted op', async () => {
    const before = Date.now();
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    const after = Date.now();
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    const startedAt = script.operations[0].execution?.startedAt;
    expect(typeof startedAt).toBe('number');
    // Dispatch stamps Date.now() at push time — must land inside the
    // [before, after] window we captured around the dispatch call.
    expect(startedAt).toBeGreaterThanOrEqual(before);
    expect(startedAt).toBeLessThanOrEqual(after);
  });

  it('round-trips execution.durationMs / mode / datasetSize / selectionSize for an edit op', async () => {
    // SELECTION → CHANGE_VALUES: the edit's execution should carry
    // the dataset size at dispatch and the size of the preceding
    // SELECTION it consumed.
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [0, 1, 2]],
      [EnumEditOperations.CHANGE_VALUES, Operator.ASSIGN, 99],
    ]);
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    const editOp = script.operations.find(
      (o) => o.method === EnumEditOperations.CHANGE_VALUES
    )!;
    expect(editOp.execution?.datasetSize).toBe(20);
    expect(editOp.execution?.selectionSize).toBe(3);
    expect(editOp.execution?.mode).toMatch(/^(worker|inline)$/);
    expect(typeof editOp.execution?.durationMs).toBe('number');
    expect(editOp.execution?.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('round-trips execution.selectionSize for a filter op from the produced selection', async () => {
    // y = 0..19 above the >= 10 threshold gives 10 indices.
    const sel = await rec.dispatch(
      EnumFilterOperations.VALUE_THRESHOLD,
      { 'Greater than or equal to': 10 },
    );
    expect(sel).toHaveLength(10);
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].execution?.selectionSize).toBe(10);
  });

  it('omits the execution field when the history entry has no execution data', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    // Replace execution with an empty shell so every field is undefined.
    rec.history[0].execution = { startedAt: NaN, inFlight: false };
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    // All fields rejected → projectExecution returned undefined → no
    // `execution` key on the wire.
    expect(script.operations[0].execution).toBeUndefined();
  });

  it('skips non-finite execution.startedAt during serialize', async () => {
    await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 5 });
    rec.history[0].execution.startedAt = NaN;
    const script = serializeHistory(rec, SAMPLE_WINDOW);
    expect(script.operations[0].execution?.startedAt).toBeUndefined();
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

  it('accepts a per-op `execution` object and round-trips every field verbatim', () => {
    const exec = {
      startedAt: 1745597000000,
      status: 'success' as const,
      durationMs: 42.5,
      mode: 'worker' as const,
      datasetSize: 120,
      selectionSize: 17,
    };
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        { method: 'VALUE_THRESHOLD', args: [{ 'Greater than': 5 }], execution: exec },
      ],
    });
    expect(script.operations[0].execution).toEqual(exec);
  });

  it('tolerates pre-execution-field operations (backward-compatible)', () => {
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [{ method: 'VALUE_THRESHOLD', args: [] }],
    });
    expect(script.operations[0].execution).toBeUndefined();
  });

  it('rejects a non-object `execution` field', () => {
    const bad = (execution: unknown) => () =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [{ method: 'VALUE_THRESHOLD', args: [], execution }],
      });
    expect(bad(42)).toThrow(/execution.*must be an object/);
    expect(bad('nope')).toThrow(/execution.*must be an object/);
    expect(bad(null)).toThrow(/execution.*must be an object/);
  });

  it('rejects non-finite numeric execution fields', () => {
    const bad = (field: string, value: unknown) => () =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [
          { method: 'VALUE_THRESHOLD', args: [], execution: { [field]: value } },
        ],
      });
    expect(bad('startedAt', '1745')).toThrow(/execution\.startedAt.*finite/);
    expect(bad('durationMs', NaN)).toThrow(/execution\.durationMs.*finite/);
    expect(bad('datasetSize', Infinity)).toThrow(/execution\.datasetSize.*finite/);
    expect(bad('selectionSize', null)).toThrow(/execution\.selectionSize.*finite/);
  });

  it('rejects invalid execution.status / execution.mode enum values', () => {
    const badStatus = () =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [
          { method: 'VALUE_THRESHOLD', args: [], execution: { status: 'ok' } },
        ],
      });
    const badMode = () =>
      parseScript({
        version: '1',
        createdAt: '2024-01-01T00:00:00.000Z',
        window: SAMPLE_WINDOW,
        operations: [
          { method: 'VALUE_THRESHOLD', args: [], execution: { mode: 'serverless' } },
        ],
      });
    expect(badStatus).toThrow(/execution\.status.*"success".*"failed"/);
    expect(badMode).toThrow(/execution\.mode.*"worker".*"inline"/);
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

  it('replay builds a fresh HistoryExecution and ignores the persisted execution audit data', async () => {
    // The persisted execution data is intentionally implausible
    // for a replay run — old timestamp, mode that doesn't match
    // local calibration, a fake duration. The contract is that
    // the dispatch site stamps its own execution record for the
    // new run, leaving the saved one untouched in the script for
    // later audit.
    const PERSISTED_STARTED = Date.UTC(2020, 0, 1);
    const script = parseScript({
      version: '1',
      createdAt: '2024-01-01T00:00:00.000Z',
      window: SAMPLE_WINDOW,
      operations: [
        {
          method: 'VALUE_THRESHOLD',
          args: [{ 'Greater than': 5 }],
          execution: {
            startedAt: PERSISTED_STARTED,
            status: 'success',
            durationMs: 9999,
            mode: 'worker',
            datasetSize: 12345,
            selectionSize: 99,
          },
        },
      ],
    });

    const fresh = makeRecord(20);
    await fresh.reload();
    const before = Date.now();
    await applyScript(fresh, script);
    const after = Date.now();

    const exec = fresh.history[0].execution;
    expect(typeof exec.startedAt).toBe('number');
    expect(exec.startedAt).not.toBe(PERSISTED_STARTED);
    expect(exec.startedAt).toBeGreaterThanOrEqual(before);
    expect(exec.startedAt).toBeLessThanOrEqual(after);
    // The replay's runtime values reflect the actual execution,
    // not the persisted audit numbers.
    expect(exec.durationMs).not.toBe(9999);
    expect(exec.datasetSize).toBe(20);  // the fresh record's size
    expect(exec.inFlight).toBe(false);
    expect(exec.status).toBe('success');
    // The original script object is unchanged — saved audit data
    // survives for later inspection even though replay overwrote
    // the in-memory field.
    expect(script.operations[0].execution?.startedAt).toBe(PERSISTED_STARTED);
    expect(script.operations[0].execution?.durationMs).toBe(9999);
    expect(script.operations[0].execution?.datasetSize).toBe(12345);
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
    // The failed entry stays in history with execution.status:
    // "failed" so the UI can render its badge.
    const failedEntry = fresh.history.find(h => h.execution.status === 'failed');
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
