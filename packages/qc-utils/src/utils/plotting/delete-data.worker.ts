import { deleteDataPointsCore } from './operation-cores'

self.onmessage = (e) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    start,
    end,
    deleteSegment,
    startTarget,
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)
  deleteDataPointsCore(
    arrayX,
    arrayY,
    deleteSegment,
    outputArrayX,
    outputArrayY,
    start,
    end,
    startTarget
  )
  self.postMessage('Done')
}
