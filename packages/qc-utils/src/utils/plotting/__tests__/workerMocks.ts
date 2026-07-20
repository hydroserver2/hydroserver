/**
 * In-process mock implementations of every worker used by `ObservationRecord`.
 *
 * The real workers are loaded via Vite's `?worker&inline` query, which is not
 * available in Vitest + happy-dom. Each mock here re-implements the logic of
 * the matching `*.worker.ts` file and runs synchronously via `queueMicrotask`,
 * which is enough to exercise every code path in `observation-record.ts`
 * end-to-end. The handler is scheduled via microtask so the caller has a chance
 * to assign `onmessage` before the response is dispatched (matching the real
 * Worker API contract).
 */

type MockWorkerInstance = {
  onmessage: ((event: { data: any }) => void) | null;
  postMessage: (data: any) => void;
  terminate: () => void;
};

function makeMockWorker(handler: (data: any) => any) {
  return class MockWorker implements MockWorkerInstance {
    onmessage: ((event: { data: any }) => void) | null = null;

    postMessage(data: any) {
      queueMicrotask(() => {
        const result = handler(data);
        if (this.onmessage) this.onmessage({ data: result });
      });
    }

    terminate() {
      // No-op: allow any scheduled microtask to run so in-flight writes to
      // shared output buffers complete before assertions read them.
    }
  };
}

export const MockDeleteDataWorker = makeMockWorker((data) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    start,
    end,
    deleteSegment,
    startTarget,
  } = data;
  const arrayX = new Float64Array(bufferX);
  const arrayY = new Float32Array(bufferY);
  const outputArrayX = new Float64Array(outputBufferX);
  const outputArrayY = new Float32Array(outputBufferY);

  let deletePtr = 0;
  let writePtr = startTarget;

  for (let readPtr = start; readPtr <= end; readPtr++) {
    if (deletePtr < deleteSegment.length && readPtr === deleteSegment[deletePtr]) {
      deletePtr++;
    } else {
      outputArrayX[writePtr] = arrayX[readPtr];
      outputArrayY[writePtr] = arrayY[readPtr];
      writePtr++;
    }
  }
  return 'Done';
});

export const MockAddDataWorker = makeMockWorker((data) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    origStart,
    origEnd,
    insertions,
    outStart,
  } = data;
  const arrayX = new Float64Array(bufferX);
  const arrayY = new Float32Array(bufferY);
  const outputArrayX = new Float64Array(outputBufferX);
  const outputArrayY = new Float32Array(outputBufferY);

  let origPtr = origStart;
  let insPtr = 0;
  let writePtr = outStart;

  while (origPtr < origEnd && insPtr < insertions.length) {
    const insX = insertions[insPtr][0];
    if (arrayX[origPtr] <= insX) {
      outputArrayX[writePtr] = arrayX[origPtr];
      outputArrayY[writePtr] = arrayY[origPtr];
      origPtr++;
    } else {
      outputArrayX[writePtr] = insX;
      outputArrayY[writePtr] = insertions[insPtr][1];
      insPtr++;
    }
    writePtr++;
  }
  while (origPtr < origEnd) {
    outputArrayX[writePtr] = arrayX[origPtr];
    outputArrayY[writePtr] = arrayY[origPtr];
    origPtr++;
    writePtr++;
  }
  while (insPtr < insertions.length) {
    outputArrayX[writePtr] = insertions[insPtr][0];
    outputArrayY[writePtr] = insertions[insPtr][1];
    insPtr++;
    writePtr++;
  }
  return 'Done';
});

export const MockChangeValuesWorker = makeMockWorker((data) => {
  const { bufferY, indexes, operator, value } = data;
  const arrayY = new Float32Array(bufferY);
  const n = indexes.length;
  if (operator === 'ADD') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] + value;
  } else if (operator === 'SUB') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] - value;
  } else if (operator === 'MULT') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] * value;
  } else if (operator === 'DIV') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] / value;
  } else if (operator === 'ASSIGN') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = value;
  }
  return 'Done';
});

export const MockInterpolateWorker = makeMockWorker((data) => {
  const { bufferX, bufferY, groups } = data;
  const arrayX = new Float64Array(bufferX);
  const arrayY = new Float32Array(bufferY);
  for (let gi = 0; gi < groups.length; gi++) {
    const { indexes, lowerIdx, upperIdx } = groups[gi];
    const lowerX = arrayX[lowerIdx];
    const lowerY = arrayY[lowerIdx];
    const upperX = arrayX[upperIdx];
    const upperY = arrayY[upperIdx];
    const xSpan = upperX - lowerX;
    const ySpan = upperY - lowerY;
    if (xSpan === 0) {
      for (let i = 0; i < indexes.length; i++) arrayY[indexes[i]] = lowerY;
      continue;
    }
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i];
      arrayY[idx] = lowerY + ((arrayX[idx] - lowerX) * ySpan) / xSpan;
    }
  }
  return 'Done';
});

export const MockDriftCorrectionWorker = makeMockWorker((data) => {
  const { bufferX, bufferY, jobs } = data;
  const arrayX = new Float64Array(bufferX);
  const arrayY = new Float32Array(bufferY);
  for (let j = 0; j < jobs.length; j++) {
    const { chunkStart, chunkEnd, startDatetime, value, extent } = jobs[j];
    for (let i = chunkStart; i < chunkEnd; i++) {
      arrayY[i] = arrayY[i] + value * ((arrayX[i] - startDatetime) / extent);
    }
  }
  return 'Done';
});

export const MockShiftDatetimesWorker = makeMockWorker((data) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    indexes,
    outStart,
    amount,
    isMonth,
    isYear,
    deltaMs,
  } = data;
  const arrayX = new Float64Array(bufferX);
  const arrayY = new Float32Array(bufferY);
  const outputArrayX = new Float64Array(outputBufferX);
  const outputArrayY = new Float32Array(outputBufferY);
  if (isMonth) {
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i];
      const d = new Date(arrayX[idx]);
      d.setMonth(d.getMonth() + amount);
      outputArrayX[outStart + i] = d.getTime();
      outputArrayY[outStart + i] = arrayY[idx];
    }
  } else if (isYear) {
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i];
      const d = new Date(arrayX[idx]);
      d.setFullYear(d.getFullYear() + amount);
      outputArrayX[outStart + i] = d.getTime();
      outputArrayY[outStart + i] = arrayY[idx];
    }
  } else {
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i];
      outputArrayX[outStart + i] = arrayX[idx] + deltaMs;
      outputArrayY[outStart + i] = arrayY[idx];
    }
  }
  return 'Done';
});

export const MockFillGapsWorker = makeMockWorker((data) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    start,
    end,
    gapsSegment,
    startTarget,
    fillDelta,
    interpolate,
    fillValue,
  } = data;
  const arrayX = new Float64Array(bufferX);
  const arrayY = new Float32Array(bufferY);
  const outputArrayX = new Float64Array(outputBufferX);
  const outputArrayY = new Float32Array(outputBufferY);

  let gapPtr = 0;
  let writePtr = startTarget;

  for (let readPtr = start; readPtr <= end; readPtr++) {
    outputArrayX[writePtr] = arrayX[readPtr];
    outputArrayY[writePtr] = arrayY[readPtr];
    writePtr++;

    if (gapPtr < gapsSegment.length && readPtr === gapsSegment[gapPtr][0]) {
      const leftIdx = gapsSegment[gapPtr][0];
      const rightIdx = gapsSegment[gapPtr][1];
      const leftDatetime = arrayX[leftIdx];
      const rightDatetime = arrayX[rightIdx];
      const leftValue = arrayY[leftIdx];
      const rightValue = arrayY[rightIdx];
      const span = rightDatetime - leftDatetime;
      const valueSpan = rightValue - leftValue;

      let nextFillDatetime = leftDatetime + fillDelta;
      while (nextFillDatetime < rightDatetime) {
        outputArrayX[writePtr] = nextFillDatetime;
        outputArrayY[writePtr] = interpolate
          ? leftValue + ((nextFillDatetime - leftDatetime) * valueSpan) / span
          : fillValue;
        writePtr++;
        nextFillDatetime += fillDelta;
      }
      gapPtr++;
    }
  }
  return 'Done';
});

export const MockFindGapsWorker = makeMockWorker((data) => {
  const { bufferX, start, endInclusive, threshold } = data;
  const arrayX = new Float64Array(bufferX);
  const pairs: number[] = [];
  let prevDatetime = arrayX[start];
  for (let i = start + 1; i <= endInclusive; i++) {
    const curr = arrayX[i];
    if (curr - prevDatetime > threshold) pairs.push(i - 1, i);
    prevDatetime = curr;
  }
  return pairs;
});

export const MockPersistenceWorker = makeMockWorker((data) => {
  const { bufferY, start, end } = data;
  const arrayY = new Float32Array(bufferY);
  const runs: number[] = [];
  if (start >= end) return runs;
  let runStart = start;
  let runValue = arrayY[start];
  for (let i = start + 1; i < end; i++) {
    const v = arrayY[i];
    if (v !== runValue) {
      runs.push(runStart, i - runStart, runValue);
      runStart = i;
      runValue = v;
    }
  }
  runs.push(runStart, end - runStart, runValue);
  return runs;
});

export const MockChangeWorker = makeMockWorker((data) => {
  const { bufferY, start, end, comparator, value } = data;
  const arrayY = new Float32Array(bufferY);
  const indexes: number[] = [];
  if (comparator === 'Less than') {
    for (let i = start; i < end; i++) if (arrayY[i] - arrayY[i - 1] < value) indexes.push(i);
  } else if (comparator === 'Less than or equal to') {
    for (let i = start; i < end; i++) if (arrayY[i] - arrayY[i - 1] <= value) indexes.push(i);
  } else if (comparator === 'Greater than') {
    for (let i = start; i < end; i++) if (arrayY[i] - arrayY[i - 1] > value) indexes.push(i);
  } else if (comparator === 'Greater than or equal to') {
    for (let i = start; i < end; i++) if (arrayY[i] - arrayY[i - 1] >= value) indexes.push(i);
  } else if (comparator === 'Equal') {
    for (let i = start; i < end; i++) if (arrayY[i] - arrayY[i - 1] == value) indexes.push(i);
  }
  return indexes;
});

export const MockRateOfChangeWorker = makeMockWorker((data) => {
  const { bufferY, start, end, comparator, value } = data;
  const arrayY = new Float32Array(bufferY);
  const indexes: number[] = [];
  if (comparator === 'Less than') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1];
      if ((arrayY[i] - prev) / Math.abs(prev) < value) indexes.push(i);
    }
  } else if (comparator === 'Less than or equal to') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1];
      if ((arrayY[i] - prev) / Math.abs(prev) <= value) indexes.push(i);
    }
  } else if (comparator === 'Greater than') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1];
      if ((arrayY[i] - prev) / Math.abs(prev) > value) indexes.push(i);
    }
  } else if (comparator === 'Greater than or equal to') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1];
      if ((arrayY[i] - prev) / Math.abs(prev) >= value) indexes.push(i);
    }
  } else if (comparator === 'Equal') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1];
      if ((arrayY[i] - prev) / Math.abs(prev) == value) indexes.push(i);
    }
  }
  return indexes;
});

export const MockValueThresholdWorker = makeMockWorker((data) => {
  const { bufferY, start, end, ops, values } = data;
  const arrayY = new Float32Array(bufferY);
  const indexes: number[] = [];
  const nFilters = ops.length;
  for (let i = start; i < end; i++) {
    const v = arrayY[i];
    let match = false;
    for (let k = 0; k < nFilters; k++) {
      const op = ops[k];
      const t = values[k];
      if (op === 0) {
        if (v < t) { match = true; break; }
      } else if (op === 1) {
        if (v <= t) { match = true; break; }
      } else if (op === 2) {
        if (v > t) { match = true; break; }
      } else if (op === 3) {
        if (v >= t) { match = true; break; }
      } else {
        if (v == t) { match = true; break; }
      }
    }
    if (match) indexes.push(i);
  }
  return indexes;
});
