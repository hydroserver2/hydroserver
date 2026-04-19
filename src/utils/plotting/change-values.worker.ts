import { changeValuesCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferY, indexes, operator, value } = e.data
  const arrayY = new Float32Array(bufferY)
  changeValuesCore(arrayY, indexes, operator, value)
  self.postMessage('Done')
}
