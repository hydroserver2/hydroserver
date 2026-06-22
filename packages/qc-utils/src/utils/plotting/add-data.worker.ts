import { addDataPointsCore } from './operation-cores'

self.onmessage = (e) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    origStart,
    origEnd,
    insertions,
    outStart,
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)
  addDataPointsCore(
    arrayX,
    arrayY,
    insertions,
    outputArrayX,
    outputArrayY,
    origStart,
    origEnd,
    outStart
  )
  self.postMessage('Done')
}
