import { describe, expect, it } from 'vitest'
import {
  getCanvasPixelLimit,
  getMaxPrintDpi,
  supportsImageExport,
  type ImageExportLimits,
} from '../plotting/imageExportLimits'

const desktop: ImageExportLimits = {
  maxWidth: 65535,
  maxHeight: 65535,
  maxPixels: 268435456,
  maxGlDimension: 16384,
}
const restricted: ImageExportLimits = {
  maxWidth: 4096,
  maxHeight: 4096,
  maxPixels: 16777216,
  maxGlDimension: 4096,
}

describe('image export limits', () => {
  it('allows large print exports beyond the old 6000-pixel ceiling', () => {
    expect(supportsImageExport(7200, 4800, desktop)).toBe(true)
    expect(supportsImageExport(10200, 13200, desktop)).toBe(true)
    expect(supportsImageExport(65535, 4096, desktop)).toBe(true)
    expect(supportsImageExport(65536, 1, desktop)).toBe(false)
  })

  it('checks total canvas area independently of width and height', () => {
    expect(supportsImageExport(20000, 20000, desktop)).toBe(false)
    expect(supportsImageExport(32767, 8192, desktop)).toBe(true)
    expect(supportsImageExport(0, 100, desktop)).toBe(false)
    expect(supportsImageExport(NaN, 100, desktop)).toBe(false)
  })

  it('calculates the highest custom DPI for the physical print size', () => {
    expect(getMaxPrintDpi(8.5, 11, restricted)).toBe(372)
    expect(getMaxPrintDpi(7, 3.5, restricted)).toBe(585)
    expect(getMaxPrintDpi(6, 4, desktop)).toBeGreaterThan(1200)
    expect(getMaxPrintDpi(0, 4, desktop)).toBe(0)
    expect(getMaxPrintDpi(NaN, 4, desktop)).toBe(0)
    const max = getMaxPrintDpi(8.5, 11, desktop)
    expect(supportsImageExport(Math.round(8.5 * max), 11 * max, desktop)).toBe(
      true
    )
    expect(
      supportsImageExport(Math.round(8.5 * (max + 1)), 11 * (max + 1), desktop)
    ).toBe(false)
  })

  it('uses engine pixel-area limits, including mobile WebKit', () => {
    expect(getCanvasPixelLimit('Chrome/144.0')).toBe(268435456)
    expect(getCanvasPixelLimit('Firefox/144.0')).toBe(536870911)
    expect(getCanvasPixelLimit('iPhone OS 18_0 CriOS/130.0')).toBe(67108864)
    expect(getCanvasPixelLimit('iPhone OS 16_0 Version/16.0')).toBe(16777216)
    expect(getCanvasPixelLimit('Macintosh Version/18.0 Safari/605.1', 5)).toBe(
      67108864
    )
    expect(getCanvasPixelLimit('unknown')).toBe(16777216)
  })
})
