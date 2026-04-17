self.onmessage = (e) => {
  const { bufferY, start, end } = e.data
  const arrayY = new Float32Array(bufferY)

  // Flat triplets: [startIndex, length, value, ...]
  const runs: number[] = []

  if (start >= end) {
    self.postMessage(runs)
    return
  }

  let runStart = start
  let runValue = arrayY[start]

  for (let i = start + 1; i < end; i++) {
    const v = arrayY[i]
    if (v !== runValue) {
      runs.push(runStart, i - runStart, runValue)
      runStart = i
      runValue = v
    }
  }
  runs.push(runStart, end - runStart, runValue)

  self.postMessage(runs)
}
