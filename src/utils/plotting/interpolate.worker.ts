self.onmessage = (e) => {
  const { bufferX, bufferY, groups } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)

  for (let gi = 0; gi < groups.length; gi++) {
    const { indexes, lowerIdx, upperIdx } = groups[gi]
    const lowerX = arrayX[lowerIdx]
    const lowerY = arrayY[lowerIdx]
    const upperX = arrayX[upperIdx]
    const upperY = arrayY[upperIdx]
    const xSpan = upperX - lowerX
    const ySpan = upperY - lowerY

    // Degenerate span (group at a buffer edge where lower == upper): keep endpoint value
    if (xSpan === 0) {
      for (let i = 0; i < indexes.length; i++) {
        arrayY[indexes[i]] = lowerY
      }
      continue
    }

    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i]
      arrayY[idx] = lowerY + ((arrayX[idx] - lowerX) * ySpan) / xSpan
    }
  }

  self.postMessage('Done')
}
