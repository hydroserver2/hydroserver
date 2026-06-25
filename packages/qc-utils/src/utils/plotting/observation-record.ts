import {
  EnumDictionary,
  EnumEditOperations,
  EnumFilterOperations,
  FilterOperation,
  HistoryItem,
  Operator,
  TimeUnit,
} from "../../types";
import { measureEllapsedTime } from "../ellapsed-time";
import { timeUnitMultipliers } from "../format";
import { findFirstGreaterOrEqual, findLastLessOrEqual } from "../observations";
// @ts-ignore
import DeleteDataWorker from "./delete-data.worker?worker&inline";
// @ts-ignore
import FillGapsWorker from "./fill-gaps.worker?worker&inline";
// @ts-ignore
import InterpolateWorker from "./interpolate.worker?worker&inline";
// @ts-ignore
import DriftCorrectionWorker from "./drift-correction.worker?worker&inline";
// @ts-ignore
import AddDataWorker from "./add-data.worker?worker&inline";
// @ts-ignore
import ShiftDatetimesWorker from "./shift-datetimes.worker?worker&inline";
// @ts-ignore
import FindGapsWorker from "./find-gaps.worker?worker&inline";
// @ts-ignore
import PersistenceWorker from "./persistence.worker?worker&inline";
// @ts-ignore
import ChangeWorker from "./change.worker?worker&inline";
// @ts-ignore
import RateOfChangeWorker from "./rate-of-change.worker?worker&inline";
// @ts-ignore
import ValueThresholdWorker from "./value-threshold.worker?worker&inline";
// @ts-ignore
import ChangeValuesWorker from "./change-values.worker?worker&inline";
import {
  addDataPointsCore,
  changeCore,
  changeValuesCore,
  deleteDataPointsCore,
  driftCorrectionCore,
  fillGapsCore,
  findGapsCore,
  interpolateCore,
  persistenceCore,
  rateOfChangeCore,
  shiftDatetimesCollection,
  valueThresholdCore,
} from "./operation-cores";
import { shouldUseWorker } from "./calibration";

/**
 * This number should approximate the number of observations that a dataset could increase by during a session.
 * The lower this number, the less memory the entire app uses.
 * Note that when a dataset number of data points increases by more than `INCREASE_AMOUNT`,
 * the `_growBuffer()` method will allocate a new buffer, and the data will be copied into it.
 */
export const INCREASE_AMOUNT = 20 * 1000;


// SharedArrayBuffer requires cross-origin isolation (COOP/COEP). When those
// headers are absent — the common consumer setup for apps that need to call
// cross-origin backends — `SharedArrayBuffer` is undefined and referencing it
// throws. Fall back to a plain ArrayBuffer; worker code paths that actually
// need SAB are already gated via `shouldUseWorker()` in calibration.
const SAB_AVAILABLE = typeof SharedArrayBuffer !== "undefined";
function makeBuffer(
  byteLength: number,
  maxByteLength?: number
): SharedArrayBuffer | ArrayBuffer {
  if (SAB_AVAILABLE) {
    return maxByteLength !== undefined
      ? new SharedArrayBuffer(byteLength, { maxByteLength })
      : new SharedArrayBuffer(byteLength);
  }
  return maxByteLength !== undefined
    ? new ArrayBuffer(byteLength, { maxByteLength })
    : new ArrayBuffer(byteLength);
}

function growBuffer(buffer: ArrayBufferLike, newByteLength: number): void {
  // SharedArrayBuffer uses `.grow()`; resizable ArrayBuffer uses `.resize()`.
  const anyBuf = buffer as { grow?: (n: number) => void; resize?: (n: number) => void };
  if (typeof anyBuf.grow === "function") {
    anyBuf.grow(newByteLength);
  } else if (typeof anyBuf.resize === "function") {
    anyBuf.resize(newByteLength);
  }
}

/**
 * Shallow per-index equality for two ascending index arrays. Used by
 * `_selection` to detect SELECTION dispatches that are echoes of the
 * preceding filter's `selected` (same length, same indices in the
 * same order — Plotly's relayout listener round-trips the indices in
 * order, so a strict per-index compare suffices and is faster than
 * Set-based set-equality on hot paths with thousands of points).
 */
function arraysShallowEqual(a: ArrayLike<number>, b: ArrayLike<number>): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

/**
 * Whether an edit operation needs the immediately preceding
 * SELECTION entry kept in history. Operations that REFERENCE the
 * selection at replay time (read indices from
 * `history[length - 2].selected`) need it kept; operations that
 * don't reference it leave a stale SELECTION below themselves
 * that would mislead a script reader, so we splice that SELECTION
 * out on dispatch.
 *
 * Drop preceding SELECTION:
 *   - ADD_POINTS — `[ts, value]` pairs are datetime-addressed and
 *     never reference any selection.
 *   - FILL_GAPS — voids any preceding selection. The panel runs
 *     its own internal Find Gaps step on commit and shows a new
 *     selection from the gaps it actually filled, so any selection
 *     that was on the plot beforehand is irrelevant to the
 *     FILL_GAPS entry.
 *
 * Keep preceding SELECTION:
 *   - CHANGE_VALUES, ASSIGN_VALUES_BULK, ASSIGN_DATETIMES_BULK
 *     read `history[length - 2].selected` directly at replay.
 *   - DELETE_POINTS, INTERPOLATE, SHIFT_DATETIMES, DRIFT_CORRECTION
 *     take selection-derived indices/ranges as args. A future
 *     script-replay path will compute those at runtime from the
 *     preceding SELECTION (per the project's reproducibility rule
 *     that index-typed args don't get serialized into the script).
 */
function consumesPrecedingSelection(
  action: EnumEditOperations,
  _args: any[]
): boolean {
  switch (action) {
    case EnumEditOperations.ADD_POINTS:
    case EnumEditOperations.FILL_GAPS:
      return false;
    default:
      return true;
  }
}

export class ObservationRecord {
  /** The generated dataset to be used for plotting */
  dataset: {
    source: {
      // Store datetimes in a Float64Array because plotly can't parse BigInts correctly.
      x: Float64Array<ArrayBufferLike>;
      y: Float32Array<ArrayBufferLike>;
    };
  } = {
      source: {
        x: new Float64Array(
          makeBuffer(
            INCREASE_AMOUNT * Float64Array.BYTES_PER_ELEMENT,
            INCREASE_AMOUNT * Float64Array.BYTES_PER_ELEMENT,
          ),
        ),
        y: new Float32Array(
          makeBuffer(
            INCREASE_AMOUNT * Float32Array.BYTES_PER_ELEMENT,
            INCREASE_AMOUNT * Float32Array.BYTES_PER_ELEMENT,
          ),
        ),
      },
    };
  history: HistoryItem[] = [];
  /**
   * Items popped off `history` by `undo()`, in undo order (top of stack
   * at the end). `redo()` re-dispatches the top. A fresh `dispatchAction`
   * / `dispatchFilter` call clears the stack — Word-style behavior where
   * a new edit invalidates the redo chain.
   */
  redoStack: HistoryItem[] = [];
  /**
   * True while `undo()` / `redo()` is replaying a captured history entry.
   * Suppresses the redo-stack clearing that otherwise fires on every new
   * dispatch, so the stack survives the internal replay.
   */
  private _isReplaying: boolean = false;
  /**
   * Set by each operation handler (or any of its subroutines) to record
   * whether a worker was actually spawned during this dispatch. Sticky-
   * upgrade semantics: the wrapper resets it to `"inline"` before the
   * handler runs, and any code that spawns a worker flips it to
   * `"worker"`. Once flipped it stays flipped for the rest of the
   * dispatch — so an op whose top-level decision is "inline" but whose
   * sub-op (e.g. `_shift` → `_deleteDataPoints`) still spawns workers
   * will honestly show `"worker"` on its history entry.
   */
  private _pendingExecutionMode: "worker" | "inline" = "inline";
  loadingTime: number | null = null;
  isLoading: boolean = true;
  rawData: {
    datetimes: Float64Array<ArrayBuffer> | number[];
    dataValues: Float32Array<ArrayBuffer> | number[];
  };

  /**
   * Inclusive epoch-ms window currently materialized into `dataset.source`.
   * `rawData` is the full series (source of truth); `dataset.source`
   * (`dataX` / `dataY`) holds only the slice within `[windowBegin,
   * windowEnd]`. Defaults to the full range, so a record with no window
   * applied behaves exactly as before. Set via `applyWindow`.
   */
  windowBegin: number = -Infinity;
  windowEnd: number = Infinity;

  constructor(dataArrays: {
    datetimes: Float64Array<ArrayBuffer> | number[];
    dataValues: Float32Array<ArrayBuffer> | number[];
  }) {
    this.history = [];
    this.rawData = dataArrays;
    this.loadData(this.rawData);
  }

  async loadData(dataArrays: {
    datetimes: Float64Array<ArrayBuffer> | number[];
    dataValues: Float32Array<ArrayBuffer> | number[];
  }) {
    if (!dataArrays) {
      return;
    }
    this.isLoading = true;
    const measurement = await measureEllapsedTime(() => {
      this._growBuffer(dataArrays.datetimes.length);
      this._resizeTo(dataArrays.datetimes.length);

      this.dataX.set(dataArrays.datetimes);
      this.dataY.set(dataArrays.dataValues);
    });

    this.loadingTime = measurement.duration;

    this.history.length = 0;
    this.isLoading = false;
  }

  /**
   * Materialize the inclusive epoch-ms window `[begin, end]` of `rawData`
   * into `dataset.source`. A real window change clears history — the new
   * window is a fresh QC baseline. An unchanged window is a no-op so an
   * unrelated reload doesn't discard in-flight edits.
   */
  async applyWindow(begin: number, end: number) {
    if (begin === this.windowBegin && end === this.windowEnd) return;
    this.windowBegin = begin;
    this.windowEnd = end;
    await this.loadData(this._windowedRaw());
  }

  /**
   * The slice of `rawData` within `[windowBegin, windowEnd]`, or the full
   * `rawData` when no window is set. `rawData` is ascending, so the bounds
   * are a pair of binary searches.
   */
  private _windowedRaw() {
    if (this.windowBegin === -Infinity && this.windowEnd === Infinity) {
      return this.rawData;
    }
    const times = this.rawData.datetimes;
    const start = findFirstGreaterOrEqual(times, this.windowBegin);
    const stop = findLastLessOrEqual(times, this.windowEnd) + 1;
    if (stop <= start) {
      return { datetimes: [] as number[], dataValues: [] as number[] };
    }
    const datetimes = Array.isArray(times)
      ? times.slice(start, stop)
      : times.subarray(start, stop);
    const values = this.rawData.dataValues;
    const dataValues = Array.isArray(values)
      ? values.slice(start, stop)
      : values.subarray(start, stop);
    return { datetimes, dataValues };
  }

  get dataX() {
    return this.dataset.source.x;
  }

  get dataY() {
    return this.dataset.source.y;
  }

  /**
   * Resizes the typed array
   * @param length The total number of elements that the view will contain
   */
  private _resizeTo(length: number) {
    // We need to resize the view to match our data length,
    // but TypedArrays using SharedArrayBuffer can't shrink.
    // Recreate the view to effectively resize it
    this.dataset.source.x = new Float64Array(
      this.dataset.source.x.buffer,
    ).subarray(0, length);

    this.dataset.source.y = new Float32Array(
      this.dataset.source.y.buffer,
    ).subarray(0, length);
  }

  /**
   * Buffer size is always in increments of `INCREASE_AMOUNT`.
   * Grows the buffer by `INCREASE_AMOUNT` in bytes if the current data doesn't fit
   * @param newLength The total number of elements that the view will contain
   */
  private _growBuffer(newLength: number) {
    const dataArrayByteSizeX = newLength * Float64Array.BYTES_PER_ELEMENT;

    let maxByteLengthNeeded = this.dataX.buffer.byteLength;
    while (dataArrayByteSizeX > maxByteLengthNeeded) {
      maxByteLengthNeeded += INCREASE_AMOUNT * Float64Array.BYTES_PER_ELEMENT;
    }

    if (
      maxByteLengthNeeded * Float64Array.BYTES_PER_ELEMENT >
      this.dataX.buffer.maxByteLength
    ) {
      // More space is needed, beyond the maxByteLength initially set, to allocate the data. A new buffer needs to be allocated.
      const outputBufferX = makeBuffer(
        this.dataX.buffer.byteLength,
        maxByteLengthNeeded * Float64Array.BYTES_PER_ELEMENT,
      );

      const outputBufferY = makeBuffer(
        this.dataY.buffer.byteLength,
        maxByteLengthNeeded * Float32Array.BYTES_PER_ELEMENT,
      );

      const outputArrayX = new Float64Array(outputBufferX);
      const outputArrayY = new Float32Array(outputBufferY);
      outputArrayX.set(this.dataX);
      outputArrayY.set(this.dataY);

      // Swap to the new array and buffer
      this.dataset.source.x = outputArrayX;
      this.dataset.source.y = outputArrayY;
    }

    if (
      this.dataX.buffer.byteLength <
      newLength * Float64Array.BYTES_PER_ELEMENT
    ) {
      growBuffer(this.dataX.buffer, newLength * Float64Array.BYTES_PER_ELEMENT);
      growBuffer(this.dataY.buffer, newLength * Float32Array.BYTES_PER_ELEMENT);
    }
  }

  /**
   * Reloads the dataset with the raw data
   */
  async reload() {
    this.loadingTime = null;
    this.isLoading = true;
    this.history.length = 0;
    await this.loadData(this._windowedRaw());
  }

  /**
   * Truncate history at `index` (inclusive), reload from raw, and
   * replay the surviving entries. Used by the "Reload from this step"
   * button in EditHistory.
   */
  async reloadHistory(index: number): Promise<number[]> {
    const newHistory = this.history.slice(0, index + 1);
    this.redoStack.length = 0;
    await this.reload();

    return await this.dispatch(newHistory.map((h) => [h.method, ...(h.args || [])]));
  }

  /** Splice the history entry at `index`, reload from raw, and replay
   *  the survivors. */
  async removeHistoryItem(index: number): Promise<number[]> {
    const newHistory = [...this.history];
    newHistory.splice(index, 1);
    this.redoStack.length = 0;
    await this.reload();
    return await this.dispatch(newHistory.map((h) => [h.method, ...(h.args || [])]));
  }

  /**
   * Undo the most recent history entry. Pushes it onto `redoStack` so a
   * subsequent `redo()` can re-apply it, then reloads from the raw
   * dataset and replays the remaining history in order.
   */
  async undo(): Promise<number[]> {
    if (!this.history.length) return [];
    const popped = this.history[this.history.length - 1];
    const newHistory = this.history.slice(0, -1);
    await this.reload();
    this.redoStack.push(popped);
    this._isReplaying = true;
    try {
      return await this.dispatch(newHistory.map((h) => [h.method, ...(h.args || [])]));
    } finally {
      this._isReplaying = false;
    }
  }

  /**
   * Re-apply the most recently undone entry from `redoStack`. The replay
   * runs through `dispatch`, which pushes a fresh history entry for it;
   * `_isReplaying` guards the redo stack from being wiped during the
   * dispatch.
   */
  async redo(): Promise<number[]> {
    if (!this.redoStack.length) return [];
    const item = this.redoStack.pop()!;
    this._isReplaying = true;
    try {
      return await this.dispatch([[item.method, ...(item.args || [])]]);
    } finally {
      this._isReplaying = false;
    }
  }

  get beginTime(): Date | null {
    if (!this.dataset.source.x.length) {
      return null;
    }
    return new Date(this.dataset.source.x[0]);
  }

  get endTime(): Date | null {
    if (!this.dataset.source.x.length) {
      return null;
    }
    return new Date(this.dataset.source.x[this.dataset.source.x.length - 1]);
  }

  /**
   * Dispatch an operation and log its signature in history.
   *
   * The selection-consuming entries below (DELETE_POINTS, INTERPOLATE,
   * SHIFT_DATETIMES, DRIFT_CORRECTION) route to thin
   * `*FromSelection` wrappers that read the target indices off
   * `history[length - 2].selected` at dispatch time, mirroring the
   * pattern CHANGE_VALUES already uses. The internal handlers
   * (`_deleteDataPoints`, `_shift`, etc.) keep their explicit-
   * indices signatures so other internal callers (e.g.
   * `_assignDatetimesBulk` → `_deleteDataPoints` + `_addDataPoints`)
   * can pass locally-computed indices without going through history.
   */
  async dispatchAction(action: EnumEditOperations, ...args: any) {
    const actions: EnumDictionary<EnumEditOperations, Function> = {
      [EnumEditOperations.ADD_POINTS]: this._addDataPoints,
      [EnumEditOperations.CHANGE_VALUES]: this._changeValues,
      [EnumEditOperations.ASSIGN_VALUES_BULK]: this._assignValuesBulk,
      [EnumEditOperations.DELETE_POINTS]: this._deleteDataPointsFromSelection,
      [EnumEditOperations.DRIFT_CORRECTION]: this._driftCorrectionFromSelection,
      [EnumEditOperations.INTERPOLATE]: this._interpolateFromSelection,
      [EnumEditOperations.SHIFT_DATETIMES]: this._shiftFromSelection,
      [EnumEditOperations.ASSIGN_DATETIMES_BULK]: this._assignDatetimesBulk,
      [EnumEditOperations.FILL_GAPS]: this._fillGaps,
    };

    let newSelection: number[] = [];
    // Declared outside the try so the catch can write
    // `status: "failed"` on the entry — even if the failure happened
    // before the try block reached the push, we still need a stable
    // reference to know whether the entry made it into history.
    let historyItem: HistoryItem | null = null;

    try {
      // A fresh dispatch breaks the redo chain (Word-style). Replays
      // from `undo()` / `redo()` set `_isReplaying` so the stack
      // survives the internal re-dispatch.
      if (!this._isReplaying) this.redoStack.length = 0;

      // Selection-consuming edits read the preceding SELECTION's
      // size at push time so the audit record reflects what the
      // handler will operate on. `consumesPrecedingSelection` gates
      // the read so non-selection edits (ADD_POINTS, FILL_GAPS)
      // don't pick up a stale value.
      const prevSelLen =
        consumesPrecedingSelection(action, args) &&
          this.history[this.history.length - 1]?.method ===
          EnumFilterOperations.SELECTION
          ? this.history[this.history.length - 1].selected?.length
          : undefined;

      historyItem = {
        method: action,
        args,
        execution: {
          startedAt: Date.now(),
          inFlight: true,
          datasetSize: this.dataset.source.x?.length ?? 0,
          selectionSize: prevSelLen,
        },
      };
      this.history.push(historyItem);

      // Pop the preceding SELECTION when this edit doesn't actually
      // consume one. A SELECTION immediately before an unrelated edit
      // (typically a stale user click or filter-driven echo) clutters
      // history and would mislead a script replay into thinking the
      // edit was selection-driven. See `consumesPrecedingSelection`
      // for the per-method rules.
      if (!consumesPrecedingSelection(action, args)) {
        const prev = this.history[this.history.length - 2];
        if (prev?.method === EnumFilterOperations.SELECTION) {
          this.history.splice(this.history.length - 2, 1);
        }
      }

      // Reset to "inline"; any worker spawn in the handler or its
      // subroutines will sticky-upgrade this to "worker" before the
      // dispatch returns.
      this._pendingExecutionMode = "inline";
      const measurement = await measureEllapsedTime(async () => {
        return await actions[action].apply(this, args);
      });
      newSelection = measurement.response;
      // Mutate via the array proxy so writes flow through Vue's
      // reactivity. Re-resolve the entry's slot via `historyItem`
      // reference rather than a captured index — the splice above
      // (or any future handler-side mutation) can shift our entry.
      // Vue 3's reactive `indexOf` normalizes raw-vs-reactive lookup;
      // `-1` means the entry was popped entirely, in which case the
      // writes are skipped.
      const newIdx = this.history.indexOf(historyItem);
      const stored = newIdx >= 0 ? this.history[newIdx] : undefined;
      if (stored) {
        stored.execution = {
          ...stored.execution,
          status: "success",
          durationMs: measurement.duration,
          mode: this._pendingExecutionMode,
          inFlight: false,
        };
      }
    } catch (e) {
      if (import.meta.env.MODE === "development") {
        console.log(
          `Failed to execute operation: ${action} with arguments: `,
          args,
        );
        console.log(e);
      }
      // Mark the entry as failed so the UI can surface it and
      // script save/load round-trips the failure state. Without
      // this the spinner would also be stuck on `inFlight: true`.
      // `historyItem` is null when the failure happened before the
      // entry was pushed (e.g. unknown action method).
      if (historyItem) {
        const failedIdx = this.history.indexOf(historyItem);
        const failed = failedIdx >= 0 ? this.history[failedIdx] : undefined;
        if (failed) {
          failed.execution = {
            ...failed.execution,
            status: "failed",
            inFlight: false,
          };
        }
      }
    }

    return newSelection;
  }

  async dispatch(
    actions:
      | EnumEditOperations
      | EnumFilterOperations
      | [EnumEditOperations | EnumFilterOperations, ...any][],
    ...args: any
  ) {
    const _handleAction = async (
      action: EnumEditOperations | EnumFilterOperations,
      args: any
    ): Promise<number[]> => {
      if (EnumFilterOperations[action as EnumFilterOperations]) {
        return await this.dispatchFilter(action as EnumFilterOperations, ...args);
      } else {
        return await this.dispatchAction(action as EnumEditOperations, ...args);
      }
    };

    if (Array.isArray(actions)) {
      let lastResponse: number[] = []
      for (let i = 0; i < actions.length; i++) {
        const method = actions[i][0]
        const actionArgs = actions[i].slice(1, actions[i].length)
        lastResponse = await _handleAction(method, actionArgs);
      }
      return lastResponse
    } else {
      return await _handleAction(actions, args);
    }
  }

  /** Filter operations do not transform the data and return a selection */
  async dispatchFilter(action: EnumFilterOperations, ...args: any): Promise<number[]> {
    const filters: EnumDictionary<EnumFilterOperations, Function> = {
      [EnumFilterOperations.FIND_GAPS]: this._findGaps,
      [EnumFilterOperations.VALUE_THRESHOLD]: this._valueThreshold,
      [EnumFilterOperations.DATETIME_RANGE]: this._datetimeRange,
      [EnumFilterOperations.PERSISTENCE]: this._persistence,
      [EnumFilterOperations.CHANGE]: this._change,
      [EnumFilterOperations.RATE_OF_CHANGE]: this._rateOfChange,
      [EnumFilterOperations.SELECTION]: this._selection,
    };

    let response = [];
    // Declared outside the try so the catch block can mark the
    // entry `status: "failed"` even when the failure happened
    // before push.
    let historyItem: HistoryItem | null = null;

    try {
      // A fresh filter dispatch breaks the redo chain (Word-style).
      // Replays from `undo()` / `redo()` set `_isReplaying` so the
      // stack survives the internal re-dispatch.
      //
      // Empty SELECTION dispatches are NOT treated as fresh edits —
      // they're either programmatic clear-selection echoes
      // (`clearSelected({recordHistory:true})`) or relayout echoes
      // that read empty `selectedpoints`. Either way, "no selection"
      // is not a new operation worth forfeiting the redo stack for.
      // Non-empty SELECTION (a real user click / lasso) still
      // invalidates redo. The relayout-induced non-empty echo of
      // our own programmatic writes is suppressed at the
      // `handleSelected` level via the `suppressNextRelayoutEcho`
      // sentinel, so it never reaches dispatchFilter.
      const newIsSelection = action === EnumFilterOperations.SELECTION;
      const isEmptySelection =
        newIsSelection &&
        (!args[0] || (Array.isArray(args[0]) && args[0].length === 0));
      if (!this._isReplaying && !isEmptySelection) {
        this.redoStack.length = 0;
      }

      historyItem = {
        method: action,
        args: args,
        execution: {
          startedAt: Date.now(),
          inFlight: true,
          datasetSize: this.dataset.source.x?.length ?? 0,
          // `selectionSize` fills in at resolve time from the filter's
          // produced selection — leave it `undefined` here.
        },
      };

      const lastItem = this.history[this.history.length - 1];

      // Filter replacement rules:
      //   - Same method → replace (rapid threshold tweaks within a
      //     single filter panel collapse into one entry).
      //   - New non-SELECTION filter, last is any filter → replace
      //     (opening a new filter panel replaces the previous active
      //     filter — only the most recent filter feeds downstream
      //     edits, which read `history[length - 2].selected`).
      //   - New SELECTION, last is a non-SELECTION filter → push and
      //     let `_selection` decide:
      //       * echo of the filter's `selected` → pop self
      //       * user-modified indices → splice out the underlying
      //         filter (manual override takes ownership)
      //       * empty → pop self AND pop the filter (selection cleared)
      //     This split keeps the SELECTION echo from `dispatchSelection`
      //     visual highlighting from clobbering the filter that just
      //     committed it.
      const lastIsFilter =
        !!EnumFilterOperations[lastItem?.method as EnumFilterOperations];
      const replace =
        lastItem?.method === action ||
        (lastIsFilter && !newIsSelection);

      let itemIdx: number;
      if (replace) {
        itemIdx = this.history.length - 1;
        this.history[itemIdx] = historyItem;
      }
      else {
        this.history.push(historyItem);
        itemIdx = this.history.length - 1;
      }
      // Reset to "inline"; any worker spawn in the handler or its
      // subroutines will sticky-upgrade this to "worker".
      this._pendingExecutionMode = "inline";
      const measurement = await measureEllapsedTime(async () => {
        return await filters[action].apply(this, args);
      });
      response = measurement.response;
      // Mutate via the array proxy so writes flow through Vue's
      // reactivity (the callsite invokes us through a proxied
      // ObservationRecord). Writing to the captured `historyItem`
      // ref directly mutates the raw object, bypasses the proxy, and
      // leaves the spinner stuck on "loading" in the UI.
      //
      // `_selection` can mutate history positions after our initial
      // push/replace (see its docblock for the full rule table): pop
      // self, pop self + prev, or splice prev. Re-resolve the entry's
      // current slot via `historyItem` reference; Vue 3 normalizes
      // `indexOf` for raw-vs-reactive lookup so the search works
      // regardless of proxy wrapping. `-1` means the entry was
      // popped entirely — skip the writes.
      const newIdx = this.history.indexOf(historyItem);
      const stored = newIdx >= 0 ? this.history[newIdx] : undefined;
      if (stored) {
        stored.selected = measurement.response;
        stored.execution = {
          ...stored.execution,
          status: "success",
          durationMs: measurement.duration,
          mode: this._pendingExecutionMode,
          selectionSize: measurement.response?.length,
          inFlight: false,
        };
      }
    } catch (e) {
      console.log(
        `Failed to execute filter operation: ${action} with arguments: `,
        args,
      );
      console.log(e);
      // Mark the entry as failed so the UI surfaces it and script
      // round-trips the failure state.
      if (historyItem) {
        const failedIdx = this.history.indexOf(historyItem);
        const failed = failedIdx >= 0 ? this.history[failedIdx] : undefined;
        if (failed) {
          failed.execution = {
            ...failed.execution,
            status: "failed",
            inFlight: false,
          };
        }
      }
    }
    return response;
  }

  /**
   * Multi-threaded apply of an arithmetic operator to Y at the previously-filtered selection.
   *  1. Selection is read from the previous history entry (the last entry is this operation itself).
   *  2. Selection indexes are sharded into disjoint chunks; workers write in place to shared Y.
   *  3. Writes are conflict-free because the selection carries distinct indexes.
   */
  private async _changeValues(
    operator: Operator,
    value: number,
  ): Promise<number[]> {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || selection.length === 0) return [];

    const N = selection.length;

    // Fast path: for small selections, the worker-startup cost dominates
    // the actual work. The calibration layer predicts the crossover per-
    // device; even the uncalibrated default profile short-circuits long
    // before any realistic edit, so no extra static floor is needed.
    const decision = shouldUseWorker(EnumEditOperations.CHANGE_VALUES, {
      datasetSize: this.dataset.source.y.length,
      selectionSize: N,
    });
    if (!decision.useWorker) {
      changeValuesCore(this.dataY, selection, operator, value);
      return [];
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, N);
    const chunkSize = Math.ceil(N / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<any>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const cStart = i * chunkSize;
      const cEnd = Math.min((i + 1) * chunkSize, N);
      if (cStart >= cEnd) break;

      const indexesChunk = selection.slice(cStart, cEnd);

      promises.push(
        new Promise((resolve) => {
          const worker = new ChangeValuesWorker();
          workers.push(worker);
          worker.postMessage({
            bufferY: this.dataY.buffer,
            indexes: indexesChunk,
            operator,
            value,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate());

    return [];
  }

  /**
   * Apply an arithmetic operator to Y in-place on the main thread. Thin
   * wrapper around {@link changeValuesCore} kept so `_assignValuesBulk`
   * and callers outside this module can use the same routine the
   * CHANGE_VALUES fast path does.
   */
  private _applyOperatorInPlace(
    indexes: ArrayLike<number>,
    operator: Operator,
    value: number,
  ): void {
    changeValuesCore(this.dataY, indexes, operator, value);
  }

  /**
   * One-shot assignment of distinct Y-values at the indices logged by the
   * previous SELECTION filter entry. Args: `(values: number[])`, where
   * `values[i]` is written to `dataY[selection[i]]`. Runs as a single
   * tight loop on the main thread — no workers, no per-row dispatch
   * ceremony. Intended for table-driven edits.
   *
   * Expected dispatch order (matches CHANGE_VALUES):
   *   [[SELECTION, indices], [ASSIGN_VALUES_BULK, values]]
   * The SELECTION entry carries the indices for history, so this op does
   * not log them again.
   */
  private async _assignValuesBulk(values: number[]): Promise<number[]> {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || !selection.length || !values?.length) return [];

    const n = Math.min(selection.length, values.length);
    const arr = this.dataY;
    for (let i = 0; i < n; i++) arr[selection[i]] = values[i];
    return [];
  }

  /**
   * One-shot assignment of distinct datetimes (epoch-ms) at the indices
   * logged by the previous SELECTION filter entry. Internally: compute
   * the replacement (x, y) pairs, do a single delete + single add — so
   * the reindex-and-sort step runs once regardless of how many rows changed.
   *
   * Expected dispatch order (matches SHIFT_DATETIMES pattern):
   *   [[SELECTION, indices], [ASSIGN_DATETIMES_BULK, datetimes]]
   */
  private async _assignDatetimesBulk(
    datetimes: number[],
  ): Promise<number[]> {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || !selection.length || !datetimes?.length) return [];

    const n = Math.min(selection.length, datetimes.length);
    const collection: [number, number][] = new Array(n);
    const sortedIndices = new Array<number>(n);
    for (let i = 0; i < n; i++) {
      collection[i] = [datetimes[i], this.dataY[selection[i]]];
      sortedIndices[i] = selection[i];
    }

    // `_deleteDataPoints` requires ascending indices.
    sortedIndices.sort((a, b) => a - b);
    await this._deleteDataPoints(sortedIndices);
    await this._addDataPoints(collection);
    return [];
  }

  /**
   * Dispatch wrapper around `_interpolate` — reads target indices
   * from `history[length - 2].selected` (the SELECTION the caller
   * dispatched immediately before this op). External callers go
   * through here; internal callers can keep using `_interpolate`
   * directly with explicit indices.
   */
  private async _interpolateFromSelection() {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || selection.length === 0) return;
    return this._interpolate(selection);
  }

  /**
   * Multi-threaded linear interpolation over the selected indexes.
   *  1. Main thread partitions the selected indexes into consecutive groups and computes each group's lower/upper anchors.
   *  2. Groups are sharded across workers (disjoint by construction, so in-place writes are safe).
   *  3. Each worker writes interpolated Y values directly into the shared Y buffer — no output copy needed since only a subset of Y changes.
   */
  private async _interpolate(index: number[]) {
    const groups = this._getConsecutiveGroups(index);
    if (groups.length === 0 || groups[0].length === 0) return;

    const len = this.dataset.source.y.length;
    const preparedGroups = groups.map((g) => ({
      indexes: g,
      lowerIdx: Math.max(0, g[0] - 1),
      upperIdx: Math.min(len - 1, g[g.length - 1] + 1),
    }));

    // Inline fast path: for small selections the worker-per-group-bucket
    // orchestration dominates. `selectionSize` is the point count we
    // actually touch; `datasetSize` stays informational.
    const decision = shouldUseWorker(EnumEditOperations.INTERPOLATE, {
      datasetSize: len,
      selectionSize: index.length,
    });
    if (!decision.useWorker) {
      interpolateCore(this.dataX, this.dataY, preparedGroups);
      return;
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = Math.min(
      navigator.hardwareConcurrency || 1,
      preparedGroups.length,
    );
    const groupsPerWorker = Math.ceil(preparedGroups.length / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<any>[] = [];
    for (let i = 0; i < numWorkers; i++) {
      const slice = preparedGroups.slice(
        i * groupsPerWorker,
        (i + 1) * groupsPerWorker,
      );
      if (slice.length === 0) break;

      promises.push(
        new Promise((resolve) => {
          const worker = new InterpolateWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            groups: slice,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate());
  }

  /**
   * Dispatch wrapper around `_shift` — reads target indices from
   * `history[length - 2].selected`. The `amount` and `unit` args
   * stay parametric on the public dispatch signature.
   */
  private async _shiftFromSelection(
    amount: number,
    unit: TimeUnit,
  ): Promise<number[]> {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || selection.length === 0) return [];
    return (await this._shift(selection, amount, unit)) ?? [];
  }

  /**
   * Shifts the selected indexes by specified amount of units. Elements are reinserted according to their datetime.
   * @param index The index of the elements to shift
   * @param amount Number of {@link TimeUnit}
   * @param unit {@link TimeUnit}
   * @returns
   */
  private async _shift(
    index: number[],
    amount: number,
    unit: TimeUnit,
  ): Promise<number[]> {
    if (index.length === 0) return [];

    const isMonth = unit === TimeUnit.MONTH;
    const isYear = unit === TimeUnit.YEAR;
    const deltaMs =
      !isMonth && !isYear ? amount * timeUnitMultipliers[unit] * 1000 : 0;

    const N = index.length;

    // Inline fast path: skip SAB allocation + the per-chunk shift
    // workers entirely; compute the collection on the main thread and
    // hand straight off to delete+add. For small selections the
    // hwConcurrency worker spawns dominate the actual shift math.
    // The downstream `_deleteDataPoints` / `_addDataPoints` make their
    // own inline-vs-worker decisions; if either spawns a worker the
    // dispatch's `_pendingExecutionMode` sticky-upgrades to "worker",
    // which is the honest label for the history badge.
    const decision = shouldUseWorker(EnumEditOperations.SHIFT_DATETIMES, {
      datasetSize: this.dataset.source.x.length,
      selectionSize: N,
    });
    if (!decision.useWorker) {
      const collection = shiftDatetimesCollection(
        this.dataX,
        this.dataY,
        index,
        { amount, isMonth, isYear, deltaMs }
      );
      await this._deleteDataPoints(index);
      // The post-add inserted indices ARE the new positions of the
      // shifted points — pass them straight back so the UI doesn't
      // have to binary-search them again.
      return (await this._addDataPoints(collection)) ?? [];
    }
    this._pendingExecutionMode = "worker";

    // Output buffers hold the shifted (x, y) pairs for the selection, in the same order as `index`
    const outputBufferX = makeBuffer(N * Float64Array.BYTES_PER_ELEMENT);
    const outputBufferY = makeBuffer(N * Float32Array.BYTES_PER_ELEMENT);

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, N);
    const chunkSize = Math.ceil(N / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<any>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const start = i * chunkSize;
      const endExc = Math.min((i + 1) * chunkSize, N);
      if (start >= endExc) break;

      const indexesChunk = index.slice(start, endExc);

      promises.push(
        new Promise((resolve) => {
          const worker = new ShiftDatetimesWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            outputBufferX,
            outputBufferY,
            indexes: indexesChunk,
            outStart: start,
            amount,
            isMonth,
            isYear,
            deltaMs,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate());

    // Build the [x, y] collection from the shifted buffers for re-insertion.
    const shiftedX = new Float64Array(outputBufferX);
    const shiftedY = new Float32Array(outputBufferY);
    const collection: [number, number][] = new Array(N);
    for (let i = 0; i < N; i++) {
      collection[i] = [shiftedX[i], shiftedY[i]];
    }

    // TODO: add dedicated method to do delete+add in one go
    await this._deleteDataPoints(index);
    return (await this._addDataPoints(collection)) ?? [];
  }

  /**
   * Detect gaps in the configured window and insert fill points using
   * either linear interpolation or a sentinel `fillValue`. Inline path:
   * single copy-with-fills sweep into freshly-allocated x/y buffers.
   * Worker path:
   *  1. The main thread scans once for gaps and computes the number of fill points per gap.
   *  2. The original array is split into equal segments; each gap is assigned to the segment containing its left index.
   *  3. Cumulative fill counts before each segment give each worker's output startTarget, ensuring no overlap.
   *  4. Each worker copies its segment to the output buffer and inserts its gap fills inline.
   *
   * @param range Optional `[startTs, endTs]` window in epoch
   *   milliseconds. Both bounds inclusive; snapped to the nearest
   *   enclosed point via binary search. Datetime-addressed (not
   *   index-addressed) so the same call survives data growth and is
   *   portable across datasets for QC history replay.
   */
  private async _fillGaps(
    gap: [number, TimeUnit],
    fill: [number, TimeUnit],
    interpolateValues: boolean,
    fillValue: number,
    range?: [number, number],
  ): Promise<number[]> {
    const len = this.dataX.length;
    if (len === 0) return [];

    const gapThresholdMs = gap[0] * timeUnitMultipliers[gap[1]] * 1000;
    const fillDelta = fill[0] * timeUnitMultipliers[fill[1]] * 1000;

    // `rangeStart` and `rangeEnd` are inclusive index bounds for the
    // detection loop below. Convert datetime bounds via binary search
    // when supplied; otherwise scan the full extent.
    const dataX = this.dataX;
    const rangeStart =
      range?.[0] != null && Number.isFinite(range[0])
        ? findFirstGreaterOrEqual(dataX, range[0])
        : 0;
    const rangeEnd =
      range?.[1] != null && Number.isFinite(range[1])
        ? findLastLessOrEqual(dataX, range[1])
        : len - 1;
    const allGaps: [number, number][] = [];
    const gapFillCounts: number[] = [];
    let totalFills = 0;
    for (let i = rangeStart + 1; i <= rangeEnd; i++) {
      const delta = dataX[i] - dataX[i - 1];
      if (delta > gapThresholdMs) {
        // Replicate the worker's fill loop to guarantee matching counts
        let count = 0;
        let t = dataX[i - 1] + fillDelta;
        while (t < dataX[i]) {
          count++;
          t += fillDelta;
        }
        if (count > 0) {
          allGaps.push([i - 1, i]);
          gapFillCounts.push(count);
          totalFills += count;
        }
      }
    }

    if (totalFills === 0) return [];

    // Compute the post-merge indices of every inserted fill point.
    // For gap k with left endpoint at orig index L_k and `c_k` fills,
    // the fills land at out indices `[L_k + Σ_{j<k} c_j + 1 ..
    // L_k + Σ_{j<k} c_j + c_k]`. Caller (the AddPoints / FillGaps UI)
    // uses these to dispatch a post-action SELECTION over the
    // newly-inserted points.
    const insertedIndices: number[] = new Array(totalFills);
    let fillsBefore = 0;
    let outPtr = 0;
    for (let k = 0; k < allGaps.length; k++) {
      const L = allGaps[k][0];
      const c = gapFillCounts[k];
      for (let j = 1; j <= c; j++) {
        insertedIndices[outPtr++] = L + fillsBefore + j;
      }
      fillsBefore += c;
    }

    const newLength = len + totalFills;

    // Output buffers sized for the new length — same allocation in
    // both the inline and worker paths.
    const newByteLengthX = newLength * Float64Array.BYTES_PER_ELEMENT;
    const newByteLengthY = newLength * Float32Array.BYTES_PER_ELEMENT;
    const outputBufferX = makeBuffer(
      newByteLengthX,
      Math.max(this.dataX.buffer.maxByteLength, newByteLengthX),
    );
    const outputBufferY = makeBuffer(
      newByteLengthY,
      Math.max(this.dataY.buffer.maxByteLength, newByteLengthY),
    );

    // Inline fast path: single copy-with-fills pass over the whole
    // array. Skips the segment partitioning + prefix-sum accounting
    // and the `hwConcurrency` worker spawns entirely. `allGaps` is
    // already in ascending order from the gap-detection scan above.
    const decision = shouldUseWorker(EnumEditOperations.FILL_GAPS, {
      datasetSize: len,
      selectionSize: totalFills,
    });
    if (!decision.useWorker) {
      const outX = new Float64Array(outputBufferX);
      const outY = new Float32Array(outputBufferY);
      fillGapsCore(
        this.dataX,
        this.dataY,
        allGaps,
        outX,
        outY,
        0,
        len - 1,
        0,
        fillDelta,
        interpolateValues,
        fillValue
      );
      this.dataset.source.x = outX;
      this.dataset.source.y = outY;
      this._resizeTo(newLength);
      return insertedIndices;
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = navigator.hardwareConcurrency || 1;
    const segmentSize = Math.ceil(len / numWorkers);

    // Partition gaps by segment (gap owned by the segment holding its left index)
    const segments: {
      start: number;
      end: number;
      gapsSegment: [number, number][];
      fillsInSegment: number;
    }[] = [];
    let gapPtr = 0;
    for (let i = 0; i < numWorkers; i++) {
      const start = i * segmentSize;
      const end = Math.min((i + 1) * segmentSize - 1, len - 1);
      const gapsSegment: [number, number][] = [];
      let fillsInSegment = 0;
      while (gapPtr < allGaps.length && allGaps[gapPtr][0] <= end) {
        gapsSegment.push(allGaps[gapPtr]);
        fillsInSegment += gapFillCounts[gapPtr];
        gapPtr++;
      }
      segments.push({ start, end, gapsSegment, fillsInSegment });
    }

    // Prefix sums of fills before each segment
    const prefixFills = new Array(numWorkers).fill(0);
    for (let i = 1; i < numWorkers; i++) {
      prefixFills[i] = prefixFills[i - 1] + segments[i - 1].fillsInSegment;
    }

    const workers: Worker[] = [];
    const promises: Promise<any>[] = [];
    for (let i = 0; i < numWorkers; i++) {
      const { start, end, gapsSegment } = segments[i];
      const startTarget = start + prefixFills[i];
      promises.push(
        new Promise((resolve) => {
          const worker = new FillGapsWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            outputBufferX,
            outputBufferY,
            start,
            end,
            gapsSegment,
            startTarget,
            fillDelta,
            interpolate: interpolateValues,
            fillValue,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate());

    this.dataset.source.x = new Float64Array(outputBufferX);
    this.dataset.source.y = new Float32Array(outputBufferY);
    this._resizeTo(newLength);
    return insertedIndices;
  }

  /**
   * Dispatch wrapper around `_deleteDataPoints` — reads target
   * indices from `history[length - 2].selected`. Internal callers
   * (`_shift`, `_assignDatetimesBulk`'s delete + add chain) keep
   * using `_deleteDataPoints` directly with locally-computed
   * indices; only the external dispatch path goes through here.
   */
  private async _deleteDataPointsFromSelection() {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || selection.length === 0) return;
    return this._deleteDataPoints(selection);
  }

  /**
   * Delete points by ascending `deleteIndices` from x/y. Inline path
   * runs a single skip-on-delete copy on the main thread; worker path:
   *  1. Main thread splits the original array into equal segments.
   *  2. Per-segment binary search locates the indexes to delete (deleteSegment) for efficient lookups.
   *  3. Cumulative deletions before each segment give each worker's output startTarget so segments don't overlap.
   *  4. Each worker walks its segment linearly, skipping deletions and copying kept elements into place.
   */
  private async _deleteDataPoints(deleteIndices: number[]) {
    const oldLen = this.dataX.length;
    const newLength = oldLen - deleteIndices.length;

    // Inline fast path: skip segmentation + worker spawns; allocate
    // fresh output buffers and run a single skip-on-delete pass over
    // the whole array on the main thread. For mid-sized datasets this
    // beats the per-segment worker orchestration handily because the
    // copy itself is just a typed-array assignment loop — spawning
    // `hwConcurrency` workers for it adds ~50–400 ms of pure overhead
    // on most devices.
    const decision = shouldUseWorker(EnumEditOperations.DELETE_POINTS, {
      datasetSize: oldLen,
      selectionSize: deleteIndices.length,
    });
    if (!decision.useWorker) {
      const outputBufferX = makeBuffer(
        this.dataX.buffer.byteLength,
        this.dataX.buffer.maxByteLength,
      );
      const outputBufferY = makeBuffer(
        this.dataY.buffer.byteLength,
        this.dataY.buffer.maxByteLength,
      );
      const outX = new Float64Array(outputBufferX);
      const outY = new Float32Array(outputBufferY);
      deleteDataPointsCore(
        this.dataX,
        this.dataY,
        deleteIndices,
        outX,
        outY,
        0,
        oldLen - 1,
        0
      );
      this.dataset.source.x = outX;
      this.dataset.source.y = outY;
      this._resizeTo(newLength);
      return;
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = navigator.hardwareConcurrency || 1;
    const segmentSize = Math.ceil(this.dataX.length / numWorkers);
    const workers: Worker[] = [];
    const segments = [];

    // Prepare segments
    for (let i = 0; i < numWorkers; i++) {
      const start = i * segmentSize;
      const end = Math.min((i + 1) * segmentSize - 1, this.dataX.length - 1);

      // Binary search to find deleteSegment within [start, end]
      const first = findFirstGreaterOrEqual(deleteIndices, start);
      const last = findLastLessOrEqual(deleteIndices, end);
      const deleteSegment = deleteIndices.slice(first, last + 1);

      segments.push({ start, end, deleteSegment });
    }

    // Compute prefix sums. These help distribute the work evenly.
    const prefixSum = new Array(numWorkers).fill(0);
    for (let i = 1; i < numWorkers; i++) {
      prefixSum[i] = prefixSum[i - 1] + segments[i - 1].deleteSegment.length;
    }

    const promises = [];

    // // To avoid workers reading from a memory address where another working is writing to, we use separate output buffers.
    const outputBufferX = makeBuffer(
      this.dataX.buffer.byteLength,
      this.dataX.buffer.maxByteLength,
    );

    const outputBufferY = makeBuffer(
      this.dataY.buffer.byteLength,
      this.dataY.buffer.maxByteLength,
    );

    // Compute startTarget for each segment and start workers
    for (let i = 0; i < numWorkers; i++) {
      const { start, end, deleteSegment } = segments[i];
      const startTarget = start - prefixSum[i];

      // Spawn workers
      promises.push(
        new Promise((resolve) => {
          const worker = new DeleteDataWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            outputBufferX,
            outputBufferY,
            start,
            end,
            deleteSegment,
            startTarget,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    // Prevents vitest from halting during execution of multiple promises
    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate()); // Important to terminate the workers

    this.dataset.source.x = new Float64Array(outputBufferX);
    this.dataset.source.y = new Float32Array(outputBufferY);
    this._resizeTo(newLength);
  }

  /**
   * Dispatch wrapper around `_driftCorrection` — reads target
   * indices from `history[length - 2].selected`, partitions them
   * into consecutive groups, and applies the same `value` drift to
   * each group as one logged operation. The internal
   * `_driftCorrection` retains its per-range `[start, end, value]`
   * signature so future callers that need distinct per-range values
   * can still use it directly.
   */
  private async _driftCorrectionFromSelection(value: number) {
    const selection = this.history[this.history.length - 2]?.selected;
    if (!selection || selection.length === 0) return;
    const groups = this._getConsecutiveGroups(selection);
    const ranges: [number, number, number][] = [];
    for (const g of groups) {
      if (g.length === 0) continue;
      ranges.push([g[0], g[g.length - 1], value]);
    }
    if (ranges.length === 0) return;
    return this._driftCorrection(ranges);
  }

  /**
   * Multi-threaded drift correction over one or more [start, end, value] ranges.
   *  1. Main thread reads each range's anchors (startDatetime, extent) once and chunks the range.
   *  2. All chunks across all ranges are flattened into jobs and distributed round-robin across a fixed pool of workers.
   *  3. Each worker applies y_n = y_0 + value * ((x_i - startDatetime) / extent) in place on its jobs.
   *  4. Batching all ranges into a single call yields a single history entry.
   */
  private async _driftCorrection(ranges: [number, number, number][]) {
    if (!ranges || ranges.length === 0) return;

    const xData = this.dataset.source.x;
    const hwConcurrency = navigator.hardwareConcurrency || 1;

    // Inline fast path: sum the range extents so the calibration
    // layer can compare the total work against worker spawn cost.
    // For tiny drift corrections (a handful of points across one
    // range) this skips `numWorkers` worker spawns entirely.
    let totalWork = 0;
    for (const [start, end] of ranges) {
      if (end > start) totalWork += end - start;
    }
    const decision = shouldUseWorker(EnumEditOperations.DRIFT_CORRECTION, {
      datasetSize: xData.length,
      selectionSize: totalWork,
    });
    if (!decision.useWorker) {
      driftCorrectionCore(xData, this.dataY, ranges);
      return;
    }
    this._pendingExecutionMode = "worker";

    type DriftJob = {
      chunkStart: number;
      chunkEnd: number;
      startDatetime: number;
      value: number;
      extent: number;
    };

    const jobs: DriftJob[] = [];
    for (const [start, end, value] of ranges) {
      if (end <= start) continue;
      const startDatetime = xData[start];
      const extent = xData[end] - startDatetime;
      if (extent === 0) continue;

      const total = end - start;
      const chunkSize = Math.max(1, Math.ceil(total / hwConcurrency));
      for (let s = start; s < end; s += chunkSize) {
        jobs.push({
          chunkStart: s,
          chunkEnd: Math.min(s + chunkSize, end),
          startDatetime,
          value,
          extent,
        });
      }
    }

    if (jobs.length === 0) return;

    // Cap workers at hardware concurrency regardless of how many ranges were passed.
    const numWorkers = Math.min(hwConcurrency, jobs.length);
    const jobBuckets: DriftJob[][] = Array.from(
      { length: numWorkers },
      () => [],
    );
    jobs.forEach((job, i) => jobBuckets[i % numWorkers].push(job));

    const workers: Worker[] = [];
    const promises: Promise<any>[] = [];

    for (const bucket of jobBuckets) {
      if (bucket.length === 0) continue;
      promises.push(
        new Promise((resolve) => {
          const worker = new DriftCorrectionWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            jobs: bucket,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate());
  }

  /** Traverses the index array and returns groups of consecutive values.
   * i.e.: `[0, 1, 3, 4, 6] => [[0, 1], [3, 4], [6]]`
   * Assumes the input array is sorted.
   * @param index: the index array (sorted)
   */
  private _getConsecutiveGroups(index: number[]): number[][] {
    const groups: number[][] = [[]];

    // Form groups of consecutive points to delete in order to minimize the number of splice operations
    index.reduce((acc: number[][], curr: number) => {
      const target: number[] = acc[acc.length - 1];

      if (!target.length || curr == target[target.length - 1] + 1) {
        target.push(curr);
      } else {
        acc.push([curr]);
      }

      return acc;
    }, groups);

    return groups;
  }

  /**
   * Adds data points using worker threads.
   *  1. Main thread sorts insertions by datetime and computes each insertion's target index via binary search on the original X.
   *  2. The original array is split into equal chunks; each insertion is assigned to the chunk containing its target index.
   *  3. `firstIns` per chunk doubles as the prefix sum of insertions placed before the chunk, giving each worker its outStart in the output buffer without overlap.
   *  4. Each worker linearly merges its original slice with its insertion slice (both already sorted by datetime) into the output buffer. Originals win on datetime ties, matching the original `findLastLessOrEqual` semantics.
   */
  private async _addDataPoints(
    dataPoints: [number, number][],
  ): Promise<number[]> {
    if (dataPoints.length === 0) return [];

    const oldLen = this.dataX.length;
    const newLength = oldLen + dataPoints.length;

    // Sort insertions by datetime ascending
    dataPoints.sort((a, b) => a[0] - b[0]);

    // Compute the post-merge index of each insertion against the
    // ORIGINAL `dataX`. The merge in `addDataPointsCore` takes
    // an original point first on ties, so each insertion lands at
    // `(count of original points with X <= T) + k` for the k-th
    // sorted insertion. Returned to callers (and stored on the
    // history entry's `selected`) so the UI can re-select the
    // newly-inserted points without re-scanning post-action.
    const insertedIndices: number[] = new Array(dataPoints.length);
    for (let k = 0; k < dataPoints.length; k++) {
      const t = dataPoints[k][0];
      const origCount = findLastLessOrEqual(this.dataX, t) + 1;
      insertedIndices[k] = origCount + k;
    }

    // Output buffers sized for the new length
    const newByteLengthX = newLength * Float64Array.BYTES_PER_ELEMENT;
    const newByteLengthY = newLength * Float32Array.BYTES_PER_ELEMENT;
    const outputBufferX = makeBuffer(
      newByteLengthX,
      Math.max(this.dataX.buffer.maxByteLength, newByteLengthX),
    );
    const outputBufferY = makeBuffer(
      newByteLengthY,
      Math.max(this.dataY.buffer.maxByteLength, newByteLengthY),
    );

    // Inline fast path: single merge pass over the whole array with
    // no worker spawns, no per-segment insertIndex binary searches,
    // and no prefix-sum accounting. Cost is dominated by the new-
    // buffer allocation (same for both paths) plus the merge loop.
    // For small/mid datasets the spawn tax on `hwConcurrency` workers
    // (~100 ms × 4 on Windows) dwarfs the entire merge.
    const decision = shouldUseWorker(EnumEditOperations.ADD_POINTS, {
      datasetSize: oldLen,
      selectionSize: dataPoints.length,
    });
    if (!decision.useWorker) {
      const outX = new Float64Array(outputBufferX);
      const outY = new Float32Array(outputBufferY);
      addDataPointsCore(
        this.dataX,
        this.dataY,
        dataPoints,
        outX,
        outY,
        0,
        oldLen,
        0
      );
      this.dataset.source.x = outX;
      this.dataset.source.y = outY;
      this._resizeTo(newLength);
      return insertedIndices;
    }
    this._pendingExecutionMode = "worker";

    // Insert index in the ORIGINAL array for each point — only the
    // worker path needs this, because it assigns insertions to a
    // specific segment via `findFirstGreaterOrEqual`.
    const insertIndex = dataPoints.map(
      (point) => findLastLessOrEqual(this.dataX, point[0]) + 1,
    );

    const numWorkers = Math.max(
      1,
      Math.min(navigator.hardwareConcurrency || 1, Math.max(oldLen, 1)),
    );
    const segmentSize = Math.ceil(Math.max(oldLen, 1) / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<any>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const origStart = i * segmentSize;
      const origEnd = Math.min((i + 1) * segmentSize, oldLen);

      // Insertions assigned to this chunk. Last chunk absorbs insertions with
      // insertIndex >= oldLen (appended past the end).
      const firstIns = findFirstGreaterOrEqual(insertIndex, origStart);
      const lastIns =
        i === numWorkers - 1
          ? dataPoints.length
          : findFirstGreaterOrEqual(insertIndex, origEnd);

      const insertions = dataPoints.slice(firstIns, lastIns);
      const outStart = origStart + firstIns;

      if (origStart >= origEnd && insertions.length === 0) continue;

      promises.push(
        new Promise((resolve) => {
          const worker = new AddDataWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            outputBufferX,
            outputBufferY,
            origStart,
            origEnd,
            insertions,
            outStart,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    if (import.meta.env.MODE !== "test") {
      await Promise.all(promises);
    }

    workers.forEach((worker) => worker.terminate());

    this.dataset.source.x = new Float64Array(outputBufferX);
    this.dataset.source.y = new Float32Array(outputBufferY);
    this._resizeTo(newLength);
    return insertedIndices;
  }

  // =======================
  // FILTER OPERATIONS
  // =======================

  /**
   * Filter by applying a set of logical operations, using worker threads.
   *  1. Main thread encodes filters as numeric opcodes + thresholds (cheaper than string compares in the hot loop).
   *  2. Workers scan disjoint chunks of Y; an index is selected if ANY filter matches (short-circuit).
   *  3. Results from each chunk are concatenated in order to preserve ascending indexes.
   *
   * Opcodes: 0=LT, 1=LTE, 2=GT, 3=GTE, 4=E.
   */
  private async _valueThreshold(
    appliedFilters: { [key: string]: number },
    range?: [number, number],
  ): Promise<number[]> {
    const keys = Object.keys(appliedFilters);
    if (keys.length === 0) return [];

    const opMap: Record<string, number> = {
      [FilterOperation.LT]: 0,
      [FilterOperation.LTE]: 1,
      [FilterOperation.GT]: 2,
      [FilterOperation.GTE]: 3,
      [FilterOperation.E]: 4,
    };
    const ops = keys.map((k) => opMap[k] ?? 4);
    const values = keys.map((k) => appliedFilters[k]);

    const dataY = this.dataset.source.y;
    const dataX = this.dataset.source.x;
    let start = 0;
    let end = dataY.length;
    if (end === 0) return [];

    // Datetime-addressed range — same shape as `_findGaps` /
    // `_persistence`. Bounds are inclusive and snapped via binary
    // search on `dataX`.
    if (range != null) {
      const [startTs, endTs] = range;
      if (startTs != null && Number.isFinite(startTs)) {
        start = findFirstGreaterOrEqual(dataX, startTs);
      }
      if (endTs != null && Number.isFinite(endTs)) {
        end = findLastLessOrEqual(dataX, endTs) + 1;
      }
    }

    if (end <= start) return [];
    const total = end - start;

    const decision = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
      datasetSize: total,
    });
    if (!decision.useWorker) {
      return valueThresholdCore(dataY, start, end, ops, values);
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, total);
    const chunkSize = Math.ceil(total / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<number[]>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const cStart = start + i * chunkSize;
      const cEnd = Math.min(start + (i + 1) * chunkSize, end);
      if (cStart >= cEnd) break;

      promises.push(
        new Promise((resolve) => {
          const worker = new ValueThresholdWorker();
          workers.push(worker);
          worker.postMessage({
            bufferY: this.dataY.buffer,
            start: cStart,
            end: cEnd,
            ops,
            values,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data as number[]);
          };
        }),
      );
    }

    const results = await Promise.all(promises);
    workers.forEach((worker) => worker.terminate());

    const selection: number[] = [];
    for (let w = 0; w < results.length; w++) {
      const arr = results[w];
      for (let k = 0; k < arr.length; k++) selection.push(arr[k]);
    }
    return selection;
  }

  /**
   * Find points where the relative rate `(curr - prev) / |prev|` satisfies the comparator, using worker threads.
   *  1. Main thread partitions scan range [1, dataY.length) into chunks; `Y[i-1]` is safely read from the shared buffer across chunk boundaries.
   *  2. Each worker runs a hoisted branch matching the comparator and returns matching indexes in ascending order.
   *  3. Main thread concatenates results in chunk order, preserving ascending order.
   */
  private async _rateOfChange(
    comparator: string,
    value: number,
    range?: [number, number],
  ): Promise<number[]> {
    const dataY = this.dataset.source.y;
    const dataX = this.dataset.source.x;
    if (dataY.length < 2) return [];

    // Same `[startTs, endTs]` ms semantics as the other filters. The
    // first index of the scan must be >= 1 because the kernel reads
    // `Y[i-1]`; clamp the snapped start up to 1 so a range whose left
    // edge falls before the first sample doesn't cause an underread.
    let start = 1;
    let end = dataY.length;
    if (range != null) {
      const [startTs, endTs] = range;
      if (startTs != null && Number.isFinite(startTs)) {
        start = Math.max(1, findFirstGreaterOrEqual(dataX, startTs));
      }
      if (endTs != null && Number.isFinite(endTs)) {
        end = findLastLessOrEqual(dataX, endTs) + 1;
      }
    }
    if (end <= start) return [];
    const total = end - start;

    const decision = shouldUseWorker(EnumFilterOperations.RATE_OF_CHANGE, {
      datasetSize: dataY.length,
    });
    if (!decision.useWorker) {
      return rateOfChangeCore(dataY, start, end, comparator, value);
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, total);
    const chunkSize = Math.ceil(total / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<number[]>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const cStart = start + i * chunkSize;
      const cEnd = Math.min(start + (i + 1) * chunkSize, end);
      if (cStart >= cEnd) break;

      promises.push(
        new Promise((resolve) => {
          const worker = new RateOfChangeWorker();
          workers.push(worker);
          worker.postMessage({
            bufferY: this.dataY.buffer,
            start: cStart,
            end: cEnd,
            comparator,
            value,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data as number[]);
          };
        }),
      );
    }

    const results = await Promise.all(promises);
    workers.forEach((worker) => worker.terminate());

    const selection: number[] = [];
    for (let w = 0; w < results.length; w++) {
      const arr = results[w];
      for (let k = 0; k < arr.length; k++) selection.push(arr[k]);
    }
    return selection;
  }

  /**
   * Select all points whose datetime falls inside `[from, to]` (inclusive).
   * `dataX` is sorted ascending, so binary search bounds the range in
   * O(log n) — no workers required. Pass `undefined` for either bound to
   * leave that side unconstrained; omitting both selects the full series.
   */
  private async _datetimeRange(
    from?: number,
    to?: number,
  ): Promise<number[]> {
    const dataX = this.dataset.source.x;
    const total = dataX.length;
    if (total === 0) return [];

    const startIdx =
      from == null ? 0 : findFirstGreaterOrEqual(dataX, from);
    const endIdx =
      to == null ? total - 1 : findLastLessOrEqual(dataX, to);

    if (startIdx > endIdx) return [];

    const selection: number[] = new Array(endIdx - startIdx + 1);
    for (let i = startIdx; i <= endIdx; i++) selection[i - startIdx] = i;
    return selection;
  }

  /**
   * SELECTION filter handler — also acts as the cleanup site for the
   * SELECTION-vs-preceding-filter interaction. `dispatchFilter` always
   * pushes (never replaces) a SELECTION when the previous entry is a
   * non-SELECTION filter; this method then decides what to keep based
   * on what the SELECTION's indices look like relative to the filter:
   *
   *  | incoming SELECTION         | preceding non-SEL filter   | result                                |
   *  | -------------------------- | -------------------------- | ------------------------------------- |
   *  | empty                      | had non-empty `selected`   | pop both — user cleared the filter    |
   *  | empty                      | had empty `selected`       | pop SELECTION — no-op echo on a       |
   *  |                            |                            |   zero-result filter, keep filter     |
   *  | empty                      | none / non-filter prev     | pop SELECTION (clear)                 |
   *  | non-empty matches prev     | (any filter)               | pop SELECTION — Plotly relayout echo  |
   *  |                            |                            |   of the filter's `selected`          |
   *  | non-empty differs from prev| (any filter)               | splice prev — user override takes     |
   *  |                            |                            |   ownership; SELECTION stands alone   |
   *  | non-empty (other cases)    | n/a                        | keep as-is (already pushed)           |
   *
   * The "Plotly echo" case exists because consumers commonly chain
   * `dispatchFilter(SOMETHING)` with `dispatchSelection(result)` for
   * visual highlighting; Plotly's debounced relayout listener then
   * fires a SELECTION carrying the same indices. Without this dedup
   * the script would grow a phantom SELECTION after every real filter.
   */
  private async _selection(index: number[]): Promise<number[]> {
    // The just-pushed SELECTION entry sits at `length - 1`; the
    // entry it would shadow is at `length - 2`.
    const prev = this.history[this.history.length - 2];
    const prevIsFilter =
      !!prev &&
      prev.method !== EnumFilterOperations.SELECTION &&
      !!EnumFilterOperations[prev.method as EnumFilterOperations];
    const prevSel: number[] | undefined = prevIsFilter
      ? (Array.isArray(prev!.selected) ? prev!.selected : undefined)
      : undefined;

    if (!index || !index.length) {
      // Empty: always drop self. Drop the underlying filter too only
      // if it was actually showing a selection that's now being
      // cleared — a zero-result filter paired with an empty SELECTION
      // echo is a no-op, not a clear.
      this.history.pop();
      if (prevSel && prevSel.length > 0) this.history.pop();
      return index;
    }

    if (prevSel && arraysShallowEqual(prevSel, index)) {
      // Programmatic echo of the preceding filter's result; drop
      // the redundant entry so the filter alone represents the action.
      this.history.pop();
    } else if (prevIsFilter) {
      // User-driven SELECTION that differs from the filter's result —
      // they've manually overridden it (clicked / lassoed / box-
      // selected). Splice out the underlying filter so the SELECTION
      // (now at the new `length - 1`) owns what's on the plot.
      this.history.splice(this.history.length - 2, 1);
    }

    return index;
  }

  /**
   * Find points where the change from the previous value satisfies the comparator, using worker threads.
   *  1. Main thread partitions scan range [1, dataY.length) into chunks (each chunk's first index safely reads Y[i-1] from the shared buffer).
   *  2. Each worker runs a hoisted branch matching the comparator and returns matching indexes in ascending order.
   *  3. Main thread concatenates results in chunk order, preserving ascending order.
   */
  private async _change(
    comparator: string,
    value: number,
    range?: [number, number],
  ): Promise<number[]> {
    const dataY = this.dataset.source.y;
    const dataX = this.dataset.source.x;
    if (dataY.length < 2) return [];

    let start = 1;
    let end = dataY.length;
    if (range != null) {
      const [startTs, endTs] = range;
      if (startTs != null && Number.isFinite(startTs)) {
        start = Math.max(1, findFirstGreaterOrEqual(dataX, startTs));
      }
      if (endTs != null && Number.isFinite(endTs)) {
        end = findLastLessOrEqual(dataX, endTs) + 1;
      }
    }
    if (end <= start) return [];
    const total = end - start;

    const decision = shouldUseWorker(EnumFilterOperations.CHANGE, {
      datasetSize: dataY.length,
    });
    if (!decision.useWorker) {
      return changeCore(dataY, start, end, comparator, value);
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, total);
    const chunkSize = Math.ceil(total / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<number[]>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const cStart = start + i * chunkSize;
      const cEnd = Math.min(start + (i + 1) * chunkSize, end);
      if (cStart >= cEnd) break;

      promises.push(
        new Promise((resolve) => {
          const worker = new ChangeWorker();
          workers.push(worker);
          worker.postMessage({
            bufferY: this.dataY.buffer,
            start: cStart,
            end: cEnd,
            comparator,
            value,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data as number[]);
          };
        }),
      );
    }

    const results = await Promise.all(promises);
    workers.forEach((worker) => worker.terminate());

    const selection: number[] = [];
    for (let w = 0; w < results.length; w++) {
      const arr = results[w];
      for (let k = 0; k < arr.length; k++) selection.push(arr[k]);
    }
    return selection;
  }

  /**
   * Find gaps in the data using worker threads.
   *  1. Main thread slices the scan range [start, end] into equal chunks with a 1-index overlap so adjacent workers observe the boundary delta correctly.
   *  2. Each worker scans its chunk and returns a flat list of [leftIdx, rightIdx] pairs for gaps whose delta exceeds the threshold.
   *  3. Main thread collects all pairs and dedups via Set — identical return shape to the original implementation.
   * @param value The time value
   * @param unit The time unit (TimeUnit)
   * @param range If specified, gap detection is restricted to this
   *   `[startTs, endTs]` window in epoch milliseconds. Both bounds
   *   are inclusive and snapped to the nearest enclosed point via
   *   binary search. Datetime-addressed (not index-addressed) so the
   *   same call survives data growth and is portable across datasets
   *   for QC history replay.
   */
  private async _findGaps(
    value: number,
    unit: TimeUnit,
    range?: [number, number],
  ): Promise<number[]> {
    const dataX = this.dataset.source.x;
    let start = 0;
    let end = dataX.length;

    if (range != null) {
      const [startTs, endTs] = range;
      if (startTs != null && Number.isFinite(startTs)) {
        start = findFirstGreaterOrEqual(dataX, startTs);
      }
      if (endTs != null && Number.isFinite(endTs)) {
        // `end` is exclusive in this function (length-style); convert
        // the inclusive datetime bound by +1 on the snapped index.
        end = findLastLessOrEqual(dataX, endTs) + 1;
      }
    }

    if (end <= start) return [];

    const threshold = value * timeUnitMultipliers[unit] * 1000;

    const decision = shouldUseWorker(EnumFilterOperations.FIND_GAPS, {
      datasetSize: end - start,
    });
    if (!decision.useWorker) {
      const pairs = findGapsCore(dataX, start, end - 1, threshold);
      const selection = new Set<number>();
      for (let k = 0; k < pairs.length; k++) selection.add(pairs[k]);
      return [...selection];
    }
    this._pendingExecutionMode = "worker";
    const total = end - start;
    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, total);
    const chunkSize = Math.ceil(total / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<number[]>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      // Chunk covers scan indexes (chunkStart, chunkEndInclusive].
      // Adjacent chunks overlap at the boundary by design — the overlapping index is the `prev`
      // for one worker and the `curr` for the other, so the boundary delta is still evaluated.
      const chunkStart = start + i * chunkSize;
      const chunkEndInclusive = Math.min(start + (i + 1) * chunkSize, end);
      if (chunkStart >= chunkEndInclusive) break;

      promises.push(
        new Promise((resolve) => {
          const worker = new FindGapsWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            start: chunkStart,
            endInclusive: chunkEndInclusive,
            threshold,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data as number[]);
          };
        }),
      );
    }

    const results = await Promise.all(promises);
    workers.forEach((worker) => worker.terminate());

    const selection = new Set<number>();
    for (let w = 0; w < results.length; w++) {
      const flat = results[w];
      for (let k = 0; k < flat.length; k++) selection.add(flat[k]);
    }
    return [...selection];
  }

  /**
   * Find points where the values are the same at least `times` in a row, using worker threads.
   *  1. Main thread splits [start, end) into chunks and each worker emits its maximal runs of equal Y values as flat (startIndex, length, value) triplets.
   *  2. Main thread stitches runs that cross chunk boundaries (same value, adjacent indexes).
   *  3. Every run whose stitched length is >= `times` contributes all of its indexes to the selection.
   *
   * Matches the Python reference implementation in `edit_service.py::persistence` — every member of a qualifying run is selected (including the run's first index).
   * @param times The minimum run length to qualify
   * @param range If specified, persistence detection is restricted
   *   to this `[startTs, endTs]` window in epoch milliseconds. Both
   *   bounds are inclusive and snapped to the nearest enclosed point
   *   via binary search on `dataX`. Datetime-addressed (not index-
   *   addressed) so the same call survives data growth and is
   *   portable across datasets for QC history replay.
   */
  private async _persistence(
    times: number,
    range?: [number, number],
  ): Promise<number[]> {
    const dataX = this.dataset.source.x;
    const dataY = this.dataset.source.y;
    let start = 0;
    let end = dataY.length;
    if (range != null) {
      const [startTs, endTs] = range;
      if (startTs != null && Number.isFinite(startTs)) {
        start = findFirstGreaterOrEqual(dataX, startTs);
      }
      if (endTs != null && Number.isFinite(endTs)) {
        // `end` is exclusive in this function; +1 to convert the
        // inclusive datetime bound to an exclusive index.
        end = findLastLessOrEqual(dataX, endTs) + 1;
      }
    }

    if (end <= start) return [];

    const total = end - start;

    const decision = shouldUseWorker(EnumFilterOperations.PERSISTENCE, {
      datasetSize: total,
    });
    if (!decision.useWorker) {
      const triplets = persistenceCore(dataY, start, end);
      const selection: number[] = [];
      for (let k = 0; k < triplets.length; k += 3) {
        const runStart = triplets[k];
        const runLength = triplets[k + 1];
        if (runLength >= times) {
          for (let j = 0; j < runLength; j++) selection.push(runStart + j);
        }
      }
      return selection;
    }
    this._pendingExecutionMode = "worker";

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, total);
    const chunkSize = Math.ceil(total / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<number[]>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const cStart = start + i * chunkSize;
      const cEnd = Math.min(start + (i + 1) * chunkSize, end);
      if (cStart >= cEnd) break;

      promises.push(
        new Promise((resolve) => {
          const worker = new PersistenceWorker();
          workers.push(worker);
          worker.postMessage({
            bufferY: this.dataY.buffer,
            start: cStart,
            end: cEnd,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data as number[]);
          };
        }),
      );
    }

    const chunkResults = await Promise.all(promises);
    workers.forEach((worker) => worker.terminate());

    // Stitch runs across chunk boundaries (runs are emitted in left-to-right order).
    // Each triplet is (startIndex, length, value).
    const mergedStart: number[] = [];
    const mergedLength: number[] = [];
    const mergedValue: number[] = [];

    for (let w = 0; w < chunkResults.length; w++) {
      const triplets = chunkResults[w];
      for (let k = 0; k < triplets.length; k += 3) {
        const runStart = triplets[k];
        const runLength = triplets[k + 1];
        const runValue = triplets[k + 2];
        const lastIdx = mergedStart.length - 1;
        if (
          lastIdx >= 0 &&
          mergedValue[lastIdx] === runValue &&
          mergedStart[lastIdx] + mergedLength[lastIdx] === runStart
        ) {
          mergedLength[lastIdx] += runLength;
        } else {
          mergedStart.push(runStart);
          mergedLength.push(runLength);
          mergedValue.push(runValue);
        }
      }
    }

    const selection: number[] = [];
    for (let r = 0; r < mergedStart.length; r++) {
      const len = mergedLength[r];
      if (len >= times) {
        const s = mergedStart[r];
        for (let k = 0; k < len; k++) selection.push(s + k);
      }
    }
    return selection;
  }
}
