self.onmessage = (e) => {
  const { bufferY, start, end, comparator, value } = e.data
  const arrayY = new Float32Array(bufferY)
  const indexes: number[] = []

  // rate = (curr - prev) / |prev|
  // Hoist comparator out of the hot loop.
  if (comparator === 'Less than') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) < value) indexes.push(i)
    }
  } else if (comparator === 'Less than or equal to') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) <= value) indexes.push(i)
    }
  } else if (comparator === 'Greater than') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) > value) indexes.push(i)
    }
  } else if (comparator === 'Greater than or equal to') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) >= value) indexes.push(i)
    }
  } else if (comparator === 'Equal') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) == value) indexes.push(i)
    }
  }

  self.postMessage(indexes)
}
