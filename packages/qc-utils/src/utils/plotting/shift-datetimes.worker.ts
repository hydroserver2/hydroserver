import { shiftDatetime } from './operation-cores'

self.onmessage = (e) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    indexes,
    outStart,
    months,
    deltaMs,
    timeZone,
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)
  const params = { months, deltaMs, timeZone }

  for (let i = 0; i < indexes.length; i++) {
    const idx = indexes[i]
    outputArrayX[outStart + i] = shiftDatetime(arrayX[idx], params)
    outputArrayY[outStart + i] = arrayY[idx]
  }

  self.postMessage('Done')
}
