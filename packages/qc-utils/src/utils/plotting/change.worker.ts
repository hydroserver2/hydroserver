import { changeCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferY, start, end, comparator, value } = e.data
  const arrayY = new Float64Array(bufferY)
  self.postMessage(changeCore(arrayY, start, end, comparator, value))
}
