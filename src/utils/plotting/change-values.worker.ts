self.onmessage = (e) => {
  const { bufferY, indexes, operator, value } = e.data
  const arrayY = new Float32Array(bufferY)
  const n = indexes.length

  // Hoist operator switch out of the hot loop.
  if (operator === 'ADD') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] + value
  } else if (operator === 'SUB') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] - value
  } else if (operator === 'MULT') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] * value
  } else if (operator === 'DIV') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] / value
  } else if (operator === 'ASSIGN') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = value
  }

  self.postMessage('Done')
}
