self.onmessage = (e) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    start,
    end,
    deleteSegment,
    startTarget,
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)

  let deletePtr = 0
  let writePtr = startTarget

  // Copy non-deleted elements to output buffer
  for (let readPtr = start; readPtr <= end; readPtr++) {
    if (
      deletePtr < deleteSegment.length &&
      readPtr === deleteSegment[deletePtr]
    ) {
      deletePtr++ // Skip deleted index
    } else {
      outputArrayX[writePtr] = arrayX[readPtr]
      outputArrayY[writePtr] = arrayY[readPtr]
      writePtr++
    }
  }


  self.postMessage('Done')
}
