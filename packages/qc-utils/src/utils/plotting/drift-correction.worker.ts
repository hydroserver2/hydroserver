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

// Worker body is a side-effect script — no imports or exports would
// otherwise mark it a TS module, so `import('./drift-correction.worker')`
// in the test harness fails with TS2306. The empty export opts this
// file into the module system without changing runtime behaviour.
export {}
