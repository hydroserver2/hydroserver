import { interpolateCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferX, bufferY, groups } = e.data
  const arrayX = new Float64Array(bufferX)
  const arrayY = new Float64Array(bufferY)
  interpolateCore(arrayX, arrayY, groups)
  self.postMessage('Done')
}
