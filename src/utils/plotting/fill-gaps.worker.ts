self.onmessage = (e) => {
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
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)

  let gapPtr = 0
  let writePtr = startTarget

  for (let readPtr = start; readPtr <= end; readPtr++) {
    // Copy original element
    outputArrayX[writePtr] = arrayX[readPtr]
    outputArrayY[writePtr] = arrayY[readPtr]
    writePtr++

    // If a gap starts at this index, insert fill points before the next original element
    if (
      gapPtr < gapsSegment.length &&
      readPtr === gapsSegment[gapPtr][0]
    ) {
      const leftIdx = gapsSegment[gapPtr][0]
      const rightIdx = gapsSegment[gapPtr][1]
      const leftDatetime = arrayX[leftIdx]
      const rightDatetime = arrayX[rightIdx]
      const leftValue = arrayY[leftIdx]
      const rightValue = arrayY[rightIdx]
      const span = rightDatetime - leftDatetime
      const valueSpan = rightValue - leftValue

      let nextFillDatetime = leftDatetime + fillDelta
      while (nextFillDatetime < rightDatetime) {
        outputArrayX[writePtr] = nextFillDatetime
        outputArrayY[writePtr] = interpolate
          ? leftValue + ((nextFillDatetime - leftDatetime) * valueSpan) / span
          : fillValue
        writePtr++
        nextFillDatetime += fillDelta
      }

      gapPtr++
    }
  }

  self.postMessage('Done')
}
