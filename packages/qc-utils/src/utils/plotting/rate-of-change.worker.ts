import { rateOfChangeCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferY, start, end, comparator, value } = e.data
  const arrayY = new Float32Array(bufferY)
  self.postMessage(rateOfChangeCore(arrayY, start, end, comparator, value))
}
