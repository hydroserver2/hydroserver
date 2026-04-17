self.onmessage = (e) => {
  const { bufferY, start, end, comparator, value } = e.data
  const arrayY = new Float32Array(bufferY)
  const indexes: number[] = []

  // Hoist comparator out of the hot loop via switched branches.
  if (comparator === 'Less than') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] < value) indexes.push(i)
    }
  } else if (comparator === 'Less than or equal to') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] <= value) indexes.push(i)
    }
  } else if (comparator === 'Greater than') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] > value) indexes.push(i)
    }
  } else if (comparator === 'Greater than or equal to') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] >= value) indexes.push(i)
    }
  } else if (comparator === 'Equal') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] == value) indexes.push(i)
    }
  }

  self.postMessage(indexes)
}
