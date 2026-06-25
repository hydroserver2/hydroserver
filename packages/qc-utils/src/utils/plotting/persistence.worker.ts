import { persistenceCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferY, start, end } = e.data
  const arrayY = new Float32Array(bufferY)
  self.postMessage(persistenceCore(arrayY, start, end))
}
