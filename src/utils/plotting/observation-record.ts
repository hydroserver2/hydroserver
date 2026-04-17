import {
  EnumDictionary,
  EnumEditOperations,
  EnumFilterOperations,
  FilterOperation,
  FilterOperationFn,
  HistoryItem,
  LogicalComparator,
  LogicalOperation,
  Operator,
  TimeUnit,
} from "../../types";
import { measureEllapsedTime } from "../ellapsed-time";
import { shiftDatetime, timeUnitMultipliers } from "../format";
import { findFirstGreaterOrEqual, findLastLessOrEqual } from "../observations";
// @ts-ignore
import DeleteDataWorker from "./delete-data.worker?worker&inline";
// @ts-ignore
import FillGapsWorker from "./fill-gaps.worker?worker&inline";

/**
 * This number should approximate the number of observations that a dataset could increase by during a session.
 * The lower this number, the less memory the entire app uses.
 * Note that when a dataset number of data points increases by more than `INCREASE_AMOUNT`,
 * the `_growBuffer()` method will allocate a new buffer, and the data will be copied into it.
 */
export const INCREASE_AMOUNT = 20 * 1000;

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
    await this.reload();
    return await this.dispatch(newHistory.map((h) => [h.method, ...(h.args || [])]));
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
      [EnumEditOperations.DELETE_POINTS]: this._deleteDataPoints,
      [EnumEditOperations.DRIFT_CORRECTION]: this._driftCorrection,
      [EnumEditOperations.INTERPOLATE]: this._interpolate,
      [EnumEditOperations.SHIFT_DATETIMES]: this._shift,
      [EnumEditOperations.FILL_GAPS]: this._fillGaps,
    };

    // TODO: consolidate with icons in EditDrawer component
    const editIcons: EnumDictionary<EnumEditOperations, string> = {
      [EnumEditOperations.ADD_POINTS]: "mdi-plus",
      [EnumEditOperations.CHANGE_VALUES]: "mdi-pencil",
      [EnumEditOperations.DELETE_POINTS]: "mdi-trash-can",
      [EnumEditOperations.DRIFT_CORRECTION]: "mdi-chart-sankey",
      [EnumEditOperations.INTERPOLATE]: "mdi-transit-connection-horizontal",
      [EnumEditOperations.SHIFT_DATETIMES]: "mdi-calendar",
      [EnumEditOperations.FILL_GAPS]: "mdi-keyboard-space",
    };

    let newSelection: number[] = [];

    try {
      const historyItem: HistoryItem = {
        method: action,
        args,
        icon: editIcons[action],
        isLoading: true,
      };
      this.history.push(historyItem);
      const measurement = await measureEllapsedTime(async () => {
        return await actions[action].apply(this, args);
      });
      newSelection = measurement.response;
      historyItem.duration = measurement.duration;
      historyItem.isLoading = false;
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
      [EnumFilterOperations.SELECTION]: "mdi-plus",
    };

    let response = [];

    try {
      const historyItem: HistoryItem = {
        method: action,
        args: args,
        icon: filterIcons[action],
        isLoading: true,
      };

      const lastItem = this.history[this.history.length - 1];

      // If the last history item is a filter, replace it
      if (EnumFilterOperations[lastItem?.method as EnumFilterOperations]) {
        this.history[this.history.length - 1] = historyItem
      }
      else {
        this.history.push(historyItem);
      }
      const measurement = await measureEllapsedTime(async () => {
        return await filters[action].apply(this, args);
      });
      response = measurement.response;
      historyItem.duration = measurement.duration;
      historyItem.selected = measurement.response;
      historyItem.isLoading = false;
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
  private _changeValues(operator: Operator, value: number): number[] {
    const operation = (x: number) => {
      switch (operator) {
        case Operator.ADD:
          return x + value;
        case Operator.ASSIGN:
          return value;
        case Operator.DIV:
          return x / value;
        case Operator.MULT:
          return x * value;
        case Operator.SUB:
          return x - value;
        default:
          return x;
      }
    };

    // The selection will be the second to last item in history. The last item is this very same operation.
    const selection = this.history[this.history.length - 2].selected

    if (selection) {
      selection.forEach((index: number) => {
        this.dataset.source.y[index] = operation(this.dataset.source.y[index]);
      });
    }

    return []
  }

  private _interpolate(index: number[]) {
    const groups = this._getConsecutiveGroups(index);

    groups.forEach((g) => {
      const start = g[0];
      const end = g[g.length - 1];

      let lowerIndex = Math.max(0, start - 1);
      let upperIndex = Math.min(this.dataset.source.y.length - 1, end + 1);

      const xData = this.dataset.source.x;
      const yData = this.dataset.source.y;
      for (let i = 0; i < g.length; i++) {
        this.dataset.source.y[g[i]] = this._interpolateLinear(
          xData[g[i]],
          xData[lowerIndex],
          yData[lowerIndex],
          xData[upperIndex],
          yData[upperIndex],
        );
      }
    });
  }

  /** Interpolate existing values in the data source */
  private _interpolateLinear(
    datetime: number,
    lowerDatetime: number,
    lowerValue: number,
    upperDatetime: number,
    upperValue: number,
  ) {
    const interpolatedValue =
      lowerValue +
      ((datetime - lowerDatetime) * (upperValue - lowerValue)) /
      (upperDatetime - lowerDatetime);

    return interpolatedValue;
  }

  /**
   * Shifts the selected indexes by specified amount of units. Elements are reinserted according to their datetime.
   * @param index The index of the elements to shift
   * @param amount Number of {@link TimeUnit}
   * @param unit {@link TimeUnit}
   * @returns
   */
  private async _shift(index: number[], amount: number, unit: TimeUnit) {
    // Collection that will be re-added using `_addDataPoints`
    const collection: [number, number][] = index.map((i) => [
      shiftDatetime(this.dataX[i], amount, unit),
      this.dataY[i],
    ]);
    // TODO: add dedicated method to do these in one go
    await this._deleteDataPoints(index);
    await this._addDataPoints(collection);
  }

  private async _fillGapsV2(
    gap: [number, TimeUnit],
    fill: [number, TimeUnit],
    interpolateValues: boolean,
    range?: [number, number],
  ) {
    const numWorkers = navigator.hardwareConcurrency || 1;
    const workers: Worker[] = [];
    const promises = [];
    const newLength = this.dataX.length;

    // To avoid workers reading from a memory address where another working is writing to, we use separate output buffers.
    const outputBufferX = new SharedArrayBuffer(this.dataX.buffer.byteLength, {
      maxByteLength: this.dataX.buffer.maxByteLength,
    });

    const outputBufferY = new SharedArrayBuffer(this.dataY.buffer.byteLength, {
      maxByteLength: this.dataY.buffer.maxByteLength,
    });

    // Compute startTarget for each segment and start workers
    for (let i = 0; i < numWorkers; i++) {
      // Spawn workers
      promises.push(
        new Promise((resolve) => {
          const worker = new FillGapsWorker();
          workers.push(worker);
          worker.postMessage({
            bufferX: this.dataX.buffer,
            bufferY: this.dataY.buffer,
            outputBufferX,
            outputBufferY,
          });
          worker.onmessage = (event: MessageEvent) => {
            resolve(event.data);
          };
        }),
      );
    }

    await Promise.all(promises);

    workers.forEach((worker) => worker.terminate()); // Important to terminate the workers

    this.dataset.source.x = new Float64Array(outputBufferX);
    this.dataset.source.y = new Float32Array(outputBufferY);
    this._resizeTo(newLength);
  }

  /**
   * Find gaps and fill them with placeholder value
   * @param gap Intervals to detect as gaps
   * @param fill Interval used to fill the detected gaps
   * @param interpolateValues If true, the new values will be linearly interpolated
   * @returns
   */
  // TODO: this needs to be improved using web workers
  private _fillGaps(
    gap: [number, TimeUnit],
    fill: [number, TimeUnit],
    interpolateValues: boolean,
    range?: [number, number],
  ) {
    const gaps = this._findGaps(gap[0], gap[1], range);

    for (let i = gaps.length - 1; i >= 0; i--) {
      const currentGap = gaps[i];
      const leftDatetime = this.dataX[currentGap[0]];
      const rightDatetime = this.dataX[currentGap[1]];
      const fillPoints: [number, number][] = [];

      // TODO: number of seconds in a year or month is not constant
      // Use setMonth and setFullYear instead
      const fillDelta = fill[0] * timeUnitMultipliers[fill[1]] * 1000;
      let nextFillDatetime = leftDatetime + fillDelta;

      while (nextFillDatetime < rightDatetime) {
        const val: number = interpolateValues
          ? this._interpolateLinear(
            nextFillDatetime,
            this.dataX[currentGap[0]],
            this.dataY[currentGap[0]],
            this.dataX[currentGap[1]],
            this.dataY[currentGap[1]],
          )
          : -9999;

        fillPoints.push([nextFillDatetime, val]);
        nextFillDatetime += fillDelta;
      }

      this._addDataPoints(fillPoints);
    }
  }

  /**
   Deletes data points from a large array using worker threads.
    1. The main thread divides the original array into equal parts to distribute work among workers.
    2. For each segment, binary search locates the indexes to delete (deleteSegment), ensuring efficient lookups.
    3. The cumulative deletions before each segment help compute the starting index (startTarget) for each worker's output, ensuring no overlap.
    4. Each worker processes its segment linearly, skipping deletions and copying kept elements to their computed positions.
    * @param deleteIndices 
   */
  // TODO: implement similar multithread solutions for other operations
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
  private _driftCorrection(start: number, end: number, value: number) {
    const xData = this.dataset.source.x;
    const yData = this.dataset.source.y;

    const startDatetime = xData[start];
    const endDatetime = xData[end];
    const extent = endDatetime - startDatetime;

    for (let i = start; i < end; i++) {
      // y_n = y_0 + G(x_i / extent)
      this.dataset.source.y[i] =
        yData[i] + value * ((xData[i] - startDatetime) / extent);
    }
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
   * Adds data points. Their insert index is determined using `findFirstGreaterOrEqual` in the x-axis.
   * @param dataPoints
   */
  private async _addDataPoints(dataPoints: [number, number][]) {
    // Check if more space is needed
    const newLength = this.dataX.length + dataPoints.length;
    this._growBuffer(newLength);
    // Sort the datapoints by datetime in reverse order
    dataPoints.sort((a, b) => {
      return a[0] - b[0];
    });

    const insertIndex = dataPoints.map((point) => {
      return findLastLessOrEqual(this.dataX, point[0]) + 1;
    });

    this._resizeTo(newLength); // The space needs to be allocated before insertion can happen

    insertIndex.push(this.dataX.length);

    // Shift elements to the right to make room for the items to insert
    let toInsert = dataPoints.length;
    for (let i = insertIndex.length - 1; i > 0; i--) {
      const left = insertIndex[i - 1];
      const right = insertIndex[i] - 1;

      for (let n = right; n >= left; n--) {
        this.dataX[n + toInsert] = this.dataX[n];
        this.dataY[n + toInsert] = this.dataY[n];
      }
      toInsert--;
      this.dataX[left + toInsert] = dataPoints[i - 1][0];
      this.dataY[left + toInsert] = dataPoints[i - 1][1];
    }
  }

  // =======================
  // FILTER OPERATIONS
  // =======================

  /**
   * Filter by applying a set of logical operations
   * @param appliedFilters
   * @returns an array of index values to select in the plot
   */
  private _valueThreshold(appliedFilters: { [key: string]: number }): number[] {
    const selection: number[] = [];

    this.dataset.source.y.forEach((value: number, index: number) => {
      if (
        Object.keys(appliedFilters).some((key) => {
          return FilterOperationFn[key as FilterOperation]?.(
            value,
            appliedFilters[key],
          );
        })
      ) {
        selection.push(index);
      }
    });

    return selection;
  }

  /**
   *
   * @param comparator
   * @param value
   * @returns
   */
  private _rateOfChange(comparator: string, value: number) {
    const selection: number[] = [];
    const dataY = this.dataset.source.y;

    for (let i = 0 + 1; i < dataY.length; i++) {
      const prev = dataY[i - 1];
      const curr = dataY[i];
      const rate = (curr - prev) / Math.abs(prev);

      if (LogicalComparator[comparator as LogicalOperation]?.(rate, value)) {
        selection.push(i);
      }
    }
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
  private _change(comparator: string, value: number) {
    const selection: number[] = [];
    const dataY = this.dataset.source.y;

    for (let i = 0 + 1; i < dataY.length; i++) {
      const prev = dataY[i - 1];
      const curr = dataY[i];
      const change = curr - prev;

      if (LogicalComparator[comparator as LogicalOperation]?.(change, value)) {
        selection.push(i);
      }
    }
    return selection;
  }

  /**
   * Find gaps in the data
   * @param value The time value
   * @param unit The time unit (TimeUnit)
   * @param range If specified, the gaps will be found only within the range
   * @returns
   */
  private _findGaps(
    value: number,
    unit: TimeUnit,
    range?: [number, number],
  ): number[] {
    const selection: [number, number][] = [];
    const dataX = this.dataset.source.x;
    let start = 0;
    let end = dataX.length;

    if (range?.[0] && range?.[1]) {
      start = range[0];
      end = range[1];
    }

    let prevDatetime = dataX[start];

    for (let i = start + 1; i <= end; i++) {
      const curr = dataX[i];
      const delta = curr - prevDatetime; // milliseconds

      if (delta > value * timeUnitMultipliers[unit] * 1000) {
        selection.push([i - 1, i]);
      }
      prevDatetime = curr;
    }

    return [...new Set(selection.flat())];
  }

  /**
   * Find points where the values are the same at least x times in a row
   * @param times The number of times in a row that points can be equal
   * @param range If specified, the points will be found only within the range
   * @returns
   */
  private _persistence(times: number, range?: [number, number]) {
    let selection: number[] = [];
    let dataY = this.dataset.source.y;
    let start = 0;
    let end = dataY.length;
    if (range?.[0] && range?.[1]) {
      start = range[0];
      end = range[1];
    }

    let prev = dataY[start];
    let stack = [];

    for (let i = start + 1; i < end; i++) {
      const curr = dataY[i];
      if (curr != prev || i === end) {
        if (stack.length >= times) {
          selection = [...selection, ...stack];
        }
        stack = [];
      } else {
        stack.push(i);
      }
    }

    return selection;
  }
}
