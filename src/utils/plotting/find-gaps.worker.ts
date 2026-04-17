self.onmessage = (e) => {
  const { bufferX, start, endInclusive, threshold } = e.data
  const arrayX = new Float64Array(bufferX)

  // Flat list of [leftIdx, rightIdx, leftIdx, rightIdx, ...] pairs
  const pairs: number[] = []

  let prevDatetime = arrayX[start]
  for (let i = start + 1; i <= endInclusive; i++) {
    const curr = arrayX[i]
    if (curr - prevDatetime > threshold) {
      pairs.push(i - 1, i)
    }
    prevDatetime = curr
  }

  self.postMessage(pairs)
}
