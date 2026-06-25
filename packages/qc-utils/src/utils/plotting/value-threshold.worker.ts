import { valueThresholdCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferY, start, end, ops, values } = e.data
  const arrayY = new Float32Array(bufferY)
  self.postMessage(valueThresholdCore(arrayY, start, end, ops, values))
}
