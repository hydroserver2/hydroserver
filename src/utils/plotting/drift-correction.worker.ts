self.onmessage = (e) => {
  const { bufferX, bufferY, jobs } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)

  // y_n = y_0 + value * ((x_i - startDatetime) / extent)
  for (let j = 0; j < jobs.length; j++) {
    const { chunkStart, chunkEnd, startDatetime, value, extent } = jobs[j]
    for (let i = chunkStart; i < chunkEnd; i++) {
      arrayY[i] = arrayY[i] + value * ((arrayX[i] - startDatetime) / extent)
    }
  }

  self.postMessage('Done')
}
