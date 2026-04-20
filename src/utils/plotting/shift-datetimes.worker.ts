self.onmessage = (e) => {
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
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)

  if (isMonth) {
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i]
      const d = new Date(arrayX[idx])
      d.setMonth(d.getMonth() + amount)
      outputArrayX[outStart + i] = d.getTime()
      outputArrayY[outStart + i] = arrayY[idx]
    }
  } else if (isYear) {
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i]
      const d = new Date(arrayX[idx])
      d.setFullYear(d.getFullYear() + amount)
      outputArrayX[outStart + i] = d.getTime()
      outputArrayY[outStart + i] = arrayY[idx]
    }
  } else {
    // Simple unit: precomputed scalar offset
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i]
      outputArrayX[outStart + i] = arrayX[idx] + deltaMs
      outputArrayY[outStart + i] = arrayY[idx]
    }
  }

  self.postMessage('Done')
}

// Worker body is a side-effect script — no imports or exports would
// otherwise mark it a TS module, so `import('./shift-datetimes.worker')`
// in the test harness fails with TS2306. The empty export opts this
// file into the module system without changing runtime behaviour.
export {}
