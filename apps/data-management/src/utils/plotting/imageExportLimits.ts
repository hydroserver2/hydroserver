export type ImageExportLimits = {
  maxWidth: number
  maxHeight: number
  maxPixels: number
  maxGlDimension: number
}

export const DEFAULT_EXPORT_LIMITS: ImageExportLimits = {
  maxWidth: 32767,
  maxHeight: 32767,
  maxPixels: 268435456,
  maxGlDimension: 4096,
}

/** Engine area limits are not exposed by the canvas API. Dimension limits are
 * probed separately below, using thin strips rather than allocating huge images.
 * Chromium: core/html/canvas/canvas_rendering_context_host.cc; WebKit: CanvasBase;
 * Gecko: gfx.max-alloc-size / 4 RGBA bytes. iOS raised its limit in 2024 (#271002).
 */
export function getCanvasPixelLimit(userAgent: string, touchPoints = 0) {
  const ios =
    /iPad|iPhone|iPod/.test(userAgent) ||
    (/Macintosh/.test(userAgent) && touchPoints > 1)
  if (ios) {
    const version = Math.max(
      Number(userAgent.match(/Version\/(\d+)/)?.[1] ?? 0),
      Number(userAgent.match(/OS (\d+)[_.]/)?.[1] ?? 0)
    )
    return version >= 18 ? 67108864 : 16777216
  }
  if (/Firefox\//.test(userAgent)) return 536870911
  if (/Chrome\/|Chromium\/|Safari\//.test(userAgent)) return 268435456
  return 16777216
}

let cachedLimits: ImageExportLimits | undefined

export function detectImageExportLimits(): ImageExportLimits {
  if (cachedLimits) return cachedLimits
  const canvas = document.createElement('canvas')
  const supports = (width: number, height: number) => {
    try {
      canvas.width = width
      canvas.height = height
      const context = canvas.getContext('2d', { willReadFrequently: true })
      if (!context) return false
      context.fillRect(width - 1, height - 1, 1, 1)
      return context.getImageData(width - 1, height - 1, 1, 1).data[3] === 255
    } catch {
      return false
    } finally {
      canvas.width = canvas.height = 1
    }
  }
  const maximum = (axis: 'width' | 'height') => {
    // Current Skia's upper dimension limit; the probe finds smaller device limits.
    let low = 0
    let high = 65536
    while (low + 1 < high) {
      const mid = Math.floor((low + high) / 2)
      if (supports(axis === 'width' ? mid : 1, axis === 'height' ? mid : 1))
        low = mid
      else high = mid
    }
    return low
  }
  const maxWidth = maximum('width')
  const maxHeight = maximum('height')
  const glCanvas = document.createElement('canvas')
  let maxGlDimension = Number.POSITIVE_INFINITY
  try {
    const gl = glCanvas.getContext('webgl')
    if (gl) {
      const viewport = gl.getParameter(gl.MAX_VIEWPORT_DIMS) as Int32Array
      maxGlDimension = Math.min(
        Number(gl.getParameter(gl.MAX_TEXTURE_SIZE)),
        Number(gl.getParameter(gl.MAX_RENDERBUFFER_SIZE)),
        viewport[0],
        viewport[1]
      )
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    }
  } catch {
    // SVG-only plots can still export when WebGL is unavailable.
  } finally {
    glCanvas.width = glCanvas.height = 1
  }
  cachedLimits = {
    maxWidth,
    maxHeight,
    maxPixels: Math.min(
      getCanvasPixelLimit(navigator.userAgent, navigator.maxTouchPoints),
      maxWidth * maxHeight
    ),
    maxGlDimension,
  }
  return cachedLimits
}

export function supportsImageExport(
  width: number,
  height: number,
  limits: ImageExportLimits
) {
  return (
    Number.isInteger(width) &&
    Number.isInteger(height) &&
    width > 0 &&
    height > 0 &&
    width <= limits.maxWidth &&
    height <= limits.maxHeight &&
    width * height <= limits.maxPixels
  )
}

export function getMaxPrintDpi(
  widthInches: number,
  heightInches: number,
  limits: ImageExportLimits
) {
  if (
    !(widthInches > 0 && heightInches > 0) ||
    !Number.isFinite(widthInches + heightInches)
  )
    return 0
  // pHYs stores pixels per metre as an unsigned 32-bit integer.
  let dpi = Math.floor(
    Math.min(
      limits.maxWidth / widthInches,
      limits.maxHeight / heightInches,
      Math.sqrt(limits.maxPixels / (widthInches * heightInches)),
      0xffffffff * 0.0254
    )
  )
  while (
    dpi > 0 &&
    !supportsImageExport(
      Math.round(widthInches * dpi),
      Math.round(heightInches * dpi),
      limits
    )
  )
    dpi--
  return dpi
}
