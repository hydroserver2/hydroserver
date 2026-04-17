self.onmessage = (e) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    origStart,
    origEnd,
    insertions,
    outStart,
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)

  let origPtr = origStart
  let insPtr = 0
  let writePtr = outStart

  // Merge original slice with pre-sorted insertions. Originals win on datetime ties
  // to preserve findLastLessOrEqual semantics (insertion placed after equal-valued originals).
  while (origPtr < origEnd && insPtr < insertions.length) {
    const insX = insertions[insPtr][0]
    if (arrayX[origPtr] <= insX) {
      outputArrayX[writePtr] = arrayX[origPtr]
      outputArrayY[writePtr] = arrayY[origPtr]
      origPtr++
    } else {
      outputArrayX[writePtr] = insX
      outputArrayY[writePtr] = insertions[insPtr][1]
      insPtr++
    }
    writePtr++
  }

  while (origPtr < origEnd) {
    outputArrayX[writePtr] = arrayX[origPtr]
    outputArrayY[writePtr] = arrayY[origPtr]
    origPtr++
    writePtr++
  }

  while (insPtr < insertions.length) {
    outputArrayX[writePtr] = insertions[insPtr][0]
    outputArrayY[writePtr] = insertions[insPtr][1]
    insPtr++
    writePtr++
  }

  self.postMessage('Done')
}
