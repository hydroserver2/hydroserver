self.onmessage = (e) => {
  const { bufferY, start, end, ops, values } = e.data
  const arrayY = new Float32Array(bufferY)
  const indexes: number[] = []
  const nFilters = ops.length

  // Opcodes: 0=LT, 1=LTE, 2=GT, 3=GTE, 4=E (START/END collapse to E)
  for (let i = start; i < end; i++) {
    const v = arrayY[i]
    let match = false
    for (let k = 0; k < nFilters; k++) {
      const op = ops[k]
      const t = values[k]
      if (op === 0) {
        if (v < t) { match = true; break }
      } else if (op === 1) {
        if (v <= t) { match = true; break }
      } else if (op === 2) {
        if (v > t) { match = true; break }
      } else if (op === 3) {
        if (v >= t) { match = true; break }
      } else {
        if (v == t) { match = true; break }
      }
    }
    if (match) indexes.push(i)
  }

  self.postMessage(indexes)
}
