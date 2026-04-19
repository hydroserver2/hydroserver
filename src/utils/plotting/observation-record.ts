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

/**
 * This number should approximate the number of observations that a dataset could increase by during a session.
 * The lower this number, the less memory the entire app uses.
 * Note that when a dataset number of data points increases by more than `INCREASE_AMOUNT`,
 * the `_growBuffer()` method will allocate a new buffer, and the data will be copied into it.
 */
export const INCREASE_AMOUNT = 20 * 1000;

/**
 * Below this selection size, CHANGE_VALUES runs inline on the main thread
 * instead of spawning inline workers. The worker-startup overhead (Windows
 * in particular can take ~100 ms each) dwarfs the write cost for small
 * edits, so the fast path cuts "3 edits" from seconds to microseconds.
 */
const CHANGE_VALUES_WORKER_THRESHOLD = 1024;

const components = ["date", "value", "qualifier"]; // TODO: `qualifier` unused for now...

export class ObservationRecord {
  /** The generated dataset to be used for plotting */
  dataset: {
    dimensions: string[];
    source: {
      // Store datetimes in a Float64Array because plotly can't parse BigInts correctly.
      x: Float64Array<SharedArrayBuffer>;
      y: Float32Array<SharedArrayBuffer>;
    };
  } = {
      dimensions: components,
      source: {
        x: new Float64Array(
          new SharedArrayBuffer(
            INCREASE_AMOUNT * Float64Array.BYTES_PER_ELEMENT,
            {
              maxByteLength: INCREASE_AMOUNT * Float64Array.BYTES_PER_ELEMENT, // Max size the array can reach
            },
          ),
        ),
        y: new Float32Array(
          new SharedArrayBuffer(
            INCREASE_AMOUNT * Float32Array.BYTES_PER_ELEMENT,
            {
              maxByteLength: INCREASE_AMOUNT * Float32Array.BYTES_PER_ELEMENT, // Max size the array can reach
            },
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
  loadingTime: number | null = null;
  isLoading: boolean = true;
  rawData: {
    datetimes: Float64Array<ArrayBuffer> | number[];
    dataValues: Float32Array<ArrayBuffer> | number[];
  };

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
      const outputBufferX = new SharedArrayBuffer(
        this.dataX.buffer.byteLength,
        {
          maxByteLength: maxByteLengthNeeded * Float64Array.BYTES_PER_ELEMENT,
        },
      );

      const outputBufferY = new SharedArrayBuffer(
        this.dataY.buffer.byteLength,
        {
          maxByteLength: maxByteLengthNeeded * Float32Array.BYTES_PER_ELEMENT,
        },
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
      this.dataX.buffer.grow(newLength * Float64Array.BYTES_PER_ELEMENT);
      this.dataY.buffer.grow(newLength * Float32Array.BYTES_PER_ELEMENT);
    }
  }

  /**
   * Reloads the dataset with the raw data
   */
  async reload() {
    this.loadingTime = null;
    this.isLoading = true;
    this.history.length = 0;
    await this.loadData(this.rawData);
  }

  /**
   * @param index
   * @returns
   */
  async reloadHistory(index: number): Promise<number[]> {
    const newHistory = this.history.slice(0, index + 1);
    this.redoStack.length = 0;
    await this.reload();

    return await this.dispatch(newHistory.map((h) => [h.method, ...(h.args || [])]));
  }

  /**
   * Remove a history item
   * @param index
   */
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

  /** Dispatch an operation and log its signature in hisotry */
  async dispatchAction(action: EnumEditOperations, ...args: any) {
    const actions: EnumDictionary<EnumEditOperations, Function> = {
      [EnumEditOperations.ADD_POINTS]: this._addDataPoints,
      [EnumEditOperations.CHANGE_VALUES]: this._changeValues,
      [EnumEditOperations.ASSIGN_VALUES_BULK]: this._assignValuesBulk,
      [EnumEditOperations.DELETE_POINTS]: this._deleteDataPoints,
      [EnumEditOperations.DRIFT_CORRECTION]: this._driftCorrection,
      [EnumEditOperations.INTERPOLATE]: this._interpolate,
      [EnumEditOperations.SHIFT_DATETIMES]: this._shift,
      [EnumEditOperations.ASSIGN_DATETIMES_BULK]: this._assignDatetimesBulk,
      [EnumEditOperations.FILL_GAPS]: this._fillGaps,
    };

    // TODO: consolidate with icons in EditDrawer component
    const editIcons: EnumDictionary<EnumEditOperations, string> = {
      [EnumEditOperations.ADD_POINTS]: "mdi-plus",
      [EnumEditOperations.CHANGE_VALUES]: "mdi-pencil",
      [EnumEditOperations.ASSIGN_VALUES_BULK]: "mdi-pencil",
      [EnumEditOperations.DELETE_POINTS]: "mdi-trash-can",
      [EnumEditOperations.DRIFT_CORRECTION]: "mdi-chart-sankey",
      [EnumEditOperations.INTERPOLATE]: "mdi-transit-connection-horizontal",
      [EnumEditOperations.SHIFT_DATETIMES]: "mdi-calendar",
      [EnumEditOperations.ASSIGN_DATETIMES_BULK]: "mdi-calendar",
      [EnumEditOperations.FILL_GAPS]: "mdi-keyboard-space",
    };

    let newSelection: number[] = [];

    try {
      // A fresh dispatch breaks the redo chain (Word-style). Replays
      // from `undo()` / `redo()` set `_isReplaying` so the stack
      // survives the internal re-dispatch.
      if (!this._isReplaying) this.redoStack.length = 0;

      const historyItem: HistoryItem = {
        method: action,
        args,
        icon: editIcons[action],
        isLoading: true,
      };
      this.history.push(historyItem);
      const itemIdx = this.history.length - 1;
      const measurement = await measureEllapsedTime(async () => {
        return await actions[action].apply(this, args);
      });
      newSelection = measurement.response;
      // Mutate via `this.history[itemIdx]` so writes flow through Vue's
      // reactive array proxy (the callsite invokes us through a proxied
      // ObservationRecord). Writing to the captured `historyItem` ref
      // directly mutates the raw object, bypasses the proxy, and leaves
      // the history entry's spinner stuck on "loading" in the UI.
      this.history[itemIdx].duration = measurement.duration;
      this.history[itemIdx].isLoading = false;
    } catch (e) {
      console.log(
        `Failed to execute operation: ${action} with arguments: `,
        args,
      );
      console.log(e);
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

    // TODO: consolidate with icons in EditDrawer component
    const filterIcons: EnumDictionary<EnumFilterOperations, string> = {
      [EnumFilterOperations.FIND_GAPS]: "mdi-plus",
      [EnumFilterOperations.PERSISTENCE]: "mdi-plus",
      [EnumFilterOperations.CHANGE]: "mdi-plus",
      [EnumFilterOperations.RATE_OF_CHANGE]: "mdi-plus",
      [EnumFilterOperations.VALUE_THRESHOLD]: "mdi-plus",
      [EnumFilterOperations.DATETIME_RANGE]: "mdi-plus",
      [EnumFilterOperations.SELECTION]: "mdi-plus",
    };

    let response = [];

    try {
      // A fresh filter dispatch breaks the redo chain (Word-style).
      // Replays from `undo()` / `redo()` set `_isReplaying` so the stack
      // survives the internal re-dispatch.
      if (!this._isReplaying) this.redoStack.length = 0;

      const historyItem: HistoryItem = {
        method: action,
        args: args,
        icon: filterIcons[action],
        isLoading: true,
      };

      const lastItem = this.history[this.history.length - 1];

      // If the last history item is a filter, replace it
      let itemIdx: number;
      if (EnumFilterOperations[lastItem?.method as EnumFilterOperations]) {
        itemIdx = this.history.length - 1;
        this.history[itemIdx] = historyItem;
      }
      else {
        this.history.push(historyItem);
        itemIdx = this.history.length - 1;
      }
      const measurement = await measureEllapsedTime(async () => {
        return await filters[action].apply(this, args);
      });
      response = measurement.response;
      // Mutate via `this.history[itemIdx]` so writes flow through Vue's
      // reactive array proxy (the callsite invokes us through a proxied
      // ObservationRecord). Writing to the captured `historyItem` ref
      // directly mutates the raw object, bypasses the proxy, and leaves
      // the history entry's spinner stuck on "loading" in the UI.
      this.history[itemIdx].duration = measurement.duration;
      this.history[itemIdx].selected = measurement.response;
      this.history[itemIdx].isLoading = false;
    } catch (e) {
      console.log(
        `Failed to execute filter operation: ${action} with arguments: `,
        args,
      );
      console.log(e);
    }
    return response;
  }

  /**
   * @param index An array containing the list of index of values to perform the operations on.
   * @param operator The operator that will be applied
   * @param value The value to use in the operation
   * @returns an array of index values to keep selected in the plot
   */
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

    // Fast path: for small selections, the worker-startup cost dominates the
    // actual work. A plain in-place loop is orders of magnitude faster.
    if (N < CHANGE_VALUES_WORKER_THRESHOLD) {
      this._applyOperatorInPlace(selection, operator, value);
      return [];
    }

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
   * Apply an arithmetic operator to Y in-place on the main thread. Used by
   * the small-selection fast path and by CHANGE_VALUES_BULK, where worker
   * startup cost would dwarf the actual write cost.
   */
  private _applyOperatorInPlace(
    indexes: ArrayLike<number>,
    operator: Operator,
    value: number,
  ): void {
    const arr = this.dataY;
    const n = indexes.length;
    if (operator === Operator.ADD) {
      for (let i = 0; i < n; i++) arr[indexes[i]] = arr[indexes[i]] + value;
    } else if (operator === Operator.SUB) {
      for (let i = 0; i < n; i++) arr[indexes[i]] = arr[indexes[i]] - value;
    } else if (operator === Operator.MULT) {
      for (let i = 0; i < n; i++) arr[indexes[i]] = arr[indexes[i]] * value;
    } else if (operator === Operator.DIV) {
      for (let i = 0; i < n; i++) arr[indexes[i]] = arr[indexes[i]] / value;
    } else if (operator === Operator.ASSIGN) {
      for (let i = 0; i < n; i++) arr[indexes[i]] = value;
    }
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

  /** Interpolate existing values in the data source */
  // private _interpolateLinear(
  //   datetime: number,
  //   lowerDatetime: number,
  //   lowerValue: number,
  //   upperDatetime: number,
  //   upperValue: number,
  // ) {
  //   const interpolatedValue =
  //     lowerValue +
  //     ((datetime - lowerDatetime) * (upperValue - lowerValue)) /
  //     (upperDatetime - lowerDatetime);

  //   return interpolatedValue;
  // }

  /**
   * Shifts the selected indexes by specified amount of units. Elements are reinserted according to their datetime.
   * @param index The index of the elements to shift
   * @param amount Number of {@link TimeUnit}
   * @param unit {@link TimeUnit}
   * @returns
   */
  private async _shift(index: number[], amount: number, unit: TimeUnit) {
    if (index.length === 0) return;

    const isMonth = unit === TimeUnit.MONTH;
    const isYear = unit === TimeUnit.YEAR;
    const deltaMs =
      !isMonth && !isYear ? amount * timeUnitMultipliers[unit] * 1000 : 0;

    const N = index.length;

    // Output buffers hold the shifted (x, y) pairs for the selection, in the same order as `index`
    const outputBufferX = new SharedArrayBuffer(
      N * Float64Array.BYTES_PER_ELEMENT,
    );
    const outputBufferY = new SharedArrayBuffer(
      N * Float32Array.BYTES_PER_ELEMENT,
    );

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
    await this._addDataPoints(collection);
  }

  /**
   * Multi-threaded version of {@link _fillGaps}.
   *  1. The main thread scans once for gaps and computes the number of fill points per gap.
   *  2. The original array is split into equal segments; each gap is assigned to the segment containing its left index.
   *  3. Cumulative fill counts before each segment give each worker's output startTarget, ensuring no overlap.
   *  4. Each worker copies its segment to the output buffer and inserts its gap fills inline.
   */
  private async _fillGaps(
    gap: [number, TimeUnit],
    fill: [number, TimeUnit],
    interpolateValues: boolean,
    range?: [number, number],
  ) {
    const len = this.dataX.length;
    if (len === 0) return;

    const gapThresholdMs = gap[0] * timeUnitMultipliers[gap[1]] * 1000;
    const fillDelta = fill[0] * timeUnitMultipliers[fill[1]] * 1000;
    const fillValue = -9999;

    const rangeStart = range?.[0] ?? 0;
    const rangeEnd = range?.[1] ?? len - 1;

    // Detect gaps as [leftIdx, rightIdx] pairs and count fills per gap
    const dataX = this.dataX;
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

    if (totalFills === 0) return;

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

    const newLength = len + totalFills;

    // Output buffers sized for the new length
    const newByteLengthX = newLength * Float64Array.BYTES_PER_ELEMENT;
    const newByteLengthY = newLength * Float32Array.BYTES_PER_ELEMENT;
    const outputBufferX = new SharedArrayBuffer(newByteLengthX, {
      maxByteLength: Math.max(this.dataX.buffer.maxByteLength, newByteLengthX),
    });
    const outputBufferY = new SharedArrayBuffer(newByteLengthY, {
      maxByteLength: Math.max(this.dataY.buffer.maxByteLength, newByteLengthY),
    });

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
  }

  /**
   Deletes data points from a large array using worker threads.
    1. The main thread divides the original array into equal parts to distribute work among workers.
    2. For each segment, binary search locates the indexes to delete (deleteSegment), ensuring efficient lookups.
    3. The cumulative deletions before each segment help compute the starting index (startTarget) for each worker's output, ensuring no overlap.
    4. Each worker processes its segment linearly, skipping deletions and copying kept elements to their computed positions.
    * @param deleteIndices 
   */
  private async _deleteDataPoints(deleteIndices: number[]) {
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
    const newLength = this.dataX.length - deleteIndices.length;

    // // To avoid workers reading from a memory address where another working is writing to, we use separate output buffers.
    const outputBufferX = new SharedArrayBuffer(this.dataX.buffer.byteLength, {
      maxByteLength: this.dataX.buffer.maxByteLength,
    });

    const outputBufferY = new SharedArrayBuffer(this.dataY.buffer.byteLength, {
      maxByteLength: this.dataY.buffer.maxByteLength,
    });

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
   *
   * @param start The start index
   * @param end The end index
   * @param value The drift amount
   */
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
  private async _addDataPoints(dataPoints: [number, number][]) {
    if (dataPoints.length === 0) return;

    const oldLen = this.dataX.length;
    const newLength = oldLen + dataPoints.length;

    // Sort insertions by datetime ascending
    dataPoints.sort((a, b) => a[0] - b[0]);

    // Insert index in the ORIGINAL array for each point
    const insertIndex = dataPoints.map(
      (point) => findLastLessOrEqual(this.dataX, point[0]) + 1,
    );

    // Output buffers sized for the new length
    const newByteLengthX = newLength * Float64Array.BYTES_PER_ELEMENT;
    const newByteLengthY = newLength * Float32Array.BYTES_PER_ELEMENT;
    const outputBufferX = new SharedArrayBuffer(newByteLengthX, {
      maxByteLength: Math.max(this.dataX.buffer.maxByteLength, newByteLengthX),
    });
    const outputBufferY = new SharedArrayBuffer(newByteLengthY, {
      maxByteLength: Math.max(this.dataY.buffer.maxByteLength, newByteLengthY),
    });

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
  }

  // =======================
  // FILTER OPERATIONS
  // =======================

  /**
   * Filter by applying a set of logical operations
   * @param appliedFilters
   * @returns an array of index values to select in the plot
   */
  /**
   * Filter by applying a set of logical operations, using worker threads.
   *  1. Main thread encodes filters as numeric opcodes + thresholds (cheaper than string compares in the hot loop).
   *  2. Workers scan disjoint chunks of Y; an index is selected if ANY filter matches (short-circuit).
   *  3. Results from each chunk are concatenated in order to preserve ascending indexes.
   *
   * Opcodes: 0=LT, 1=LTE, 2=GT, 3=GTE, 4=E.
   */
  private async _valueThreshold(appliedFilters: {
    [key: string]: number;
  }): Promise<number[]> {
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
    const total = dataY.length;
    if (total === 0) return [];

    const numWorkers = Math.min(navigator.hardwareConcurrency || 1, total);
    const chunkSize = Math.ceil(total / numWorkers);

    const workers: Worker[] = [];
    const promises: Promise<number[]>[] = [];

    for (let i = 0; i < numWorkers; i++) {
      const cStart = i * chunkSize;
      const cEnd = Math.min((i + 1) * chunkSize, total);
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
   *
   * @param comparator
   * @param value
   * @returns
   */
  /**
   * Find points where the relative rate `(curr - prev) / |prev|` satisfies the comparator, using worker threads.
   *  1. Main thread partitions scan range [1, dataY.length) into chunks; `Y[i-1]` is safely read from the shared buffer across chunk boundaries.
   *  2. Each worker runs a hoisted branch matching the comparator and returns matching indexes in ascending order.
   *  3. Main thread concatenates results in chunk order, preserving ascending order.
   */
  private async _rateOfChange(
    comparator: string,
    value: number,
  ): Promise<number[]> {
    const dataY = this.dataset.source.y;
    if (dataY.length < 2) return [];

    const start = 1;
    const end = dataY.length;
    const total = end - start;
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
   * @param index
   * @returns
   */
  private async _selection(index: number[]): Promise<number[]> {
    // If clearing selection, remove the history item
    if (!index || !index.length) {
      this.history.pop();
    }

    return index;
  }

  /**
   *
   * @param comparator
   * @param value
   * @returns
   */
  /**
   * Find points where the change from the previous value satisfies the comparator, using worker threads.
   *  1. Main thread partitions scan range [1, dataY.length) into chunks (each chunk's first index safely reads Y[i-1] from the shared buffer).
   *  2. Each worker runs a hoisted branch matching the comparator and returns matching indexes in ascending order.
   *  3. Main thread concatenates results in chunk order, preserving ascending order.
   */
  private async _change(comparator: string, value: number): Promise<number[]> {
    const dataY = this.dataset.source.y;
    if (dataY.length < 2) return [];

    const start = 1;
    const end = dataY.length;
    const total = end - start;
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
   * @param range If specified, the gaps will be found only within the range
   */
  private async _findGaps(
    value: number,
    unit: TimeUnit,
    range?: [number, number],
  ): Promise<number[]> {
    const dataX = this.dataset.source.x;
    let start = 0;
    let end = dataX.length;

    if (range?.[0] && range?.[1]) {
      start = range[0];
      end = range[1];
    }

    if (end <= start) return [];

    const threshold = value * timeUnitMultipliers[unit] * 1000;
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
   * @param range If specified, the points will be found only within the range
   */
  private async _persistence(
    times: number,
    range?: [number, number],
  ): Promise<number[]> {
    const dataY = this.dataset.source.y;
    let start = 0;
    let end = dataY.length;
    if (range?.[0] && range?.[1]) {
      start = range[0];
      end = range[1];
    }

    if (end <= start) return [];

    const total = end - start;
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
