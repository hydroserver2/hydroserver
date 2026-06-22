import { fillGapsCore } from './operation-cores'

self.onmessage = (e) => {
  const {
    bufferX,
    bufferY,
    outputBufferX,
    outputBufferY,
    start,
    end,
    gapsSegment,
    startTarget,
    fillDelta,
    interpolate,
    fillValue,
  } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float32Array(bufferY)
  const outputArrayX = new Float64Array(outputBufferX)
  const outputArrayY = new Float32Array(outputBufferY)
  fillGapsCore(
    arrayX,
    arrayY,
    gapsSegment,
    outputArrayX,
    outputArrayY,
    start,
    end,
    startTarget,
    fillDelta,
    interpolate,
    fillValue
  )
  self.postMessage('Done')
}
