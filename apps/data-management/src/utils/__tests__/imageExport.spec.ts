import { describe, expect, it } from 'vitest'
import { crc32 } from 'node:zlib'
import { getFigureExportSize, setPngDpi } from '../plotting/imageExport'

const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jz1kAAAAASUVORK5CYII=',
  'base64'
)

function chunks(bytes: Uint8Array) {
  const buffer = Buffer.from(bytes)
  const result: { kind: string; data: Buffer; crc: number }[] = []
  for (let offset = 8; offset < buffer.length;) {
    const length = buffer.readUInt32BE(offset)
    result.push({
      kind: buffer.toString('ascii', offset + 4, offset + 8),
      data: buffer.subarray(offset + 8, offset + 8 + length),
      crc: buffer.readUInt32BE(offset + 8 + length),
    })
    offset += length + 12
  }
  return result
}

describe('image export resolution', () => {
  it('uses physical print width and DPI while preserving the chart proportions', () => {
    const source = { width: 1200, height: 900 }
    const print = getFigureExportSize(source.width, source.height, {
      mode: 'print',
      widthInches: 6,
      heightInches: 4.5,
      dpi: 300,
    })
    expect(print).toEqual({ width: 1800, height: 1350, scale: 1.5, dpi: 300 })
    const high = getFigureExportSize(source.width, source.height, {
      mode: 'print',
      widthInches: 6,
      heightInches: 4.5,
      dpi: 600,
    })
    expect(high).toEqual({ width: 3600, height: 2700, scale: 3, dpi: 600 })
    expect(source).toEqual({ width: 1200, height: 900 })
  })

  it('supports screen scaling and fractional custom print sizes', () => {
    expect(
      getFigureExportSize(1000, 700, { mode: 'screen', scale: 2 })
    ).toEqual({
      width: 2000,
      height: 1400,
      scale: 2,
      dpi: 96,
    })
    expect(
      getFigureExportSize(1000, 700, {
        mode: 'print',
        widthInches: 3.5,
        heightInches: 2.45,
        dpi: 300,
      })
    ).toEqual({ width: 1050, height: 735, scale: 1.05, dpi: 300 })
  })

  it('uses independent print height and rounds physical sizes to the nearest pixel', () => {
    expect(
      getFigureExportSize(1200, 900, {
        mode: 'print',
        widthInches: 6,
        heightInches: 4,
        dpi: 300,
      })
    ).toEqual({ width: 1800, height: 1200, scale: 1.5, dpi: 300 })
    expect(
      getFigureExportSize(1200, 900, {
        mode: 'print',
        widthInches: 6,
        heightInches: 10 / 2.54,
        dpi: 300,
      })
    ).toEqual({ width: 1800, height: 1181, scale: 1.5, dpi: 300 })
    expect(
      getFigureExportSize(1200, 900, {
        mode: 'print',
        widthInches: 3,
        heightInches: 6,
        dpi: 300,
      })
    ).toEqual({ width: 900, height: 1800, scale: 0.75, dpi: 300 })
  })
})

describe('PNG print resolution metadata', () => {
  it('writes valid DPI metadata without changing image pixels or other chunks', () => {
    const result = chunks(setPngDpi(png, 300))
    const resolution = result.find((chunk) => chunk.kind === 'pHYs')!
    expect(result.map((chunk) => chunk.kind)).toEqual([
      'IHDR',
      'pHYs',
      'IDAT',
      'IEND',
    ])
    expect(resolution.data.readUInt32BE(0) * 0.0254).toBeCloseTo(300, 1)
    expect(resolution.data.readUInt32BE(4) * 0.0254).toBeCloseTo(300, 1)
    expect(resolution.data[8]).toBe(1)
    expect(resolution.crc).toBe(
      crc32(Buffer.concat([Buffer.from('pHYs'), resolution.data]))
    )
    expect(result.filter((chunk) => chunk.kind !== 'pHYs')).toEqual(chunks(png))
  })

  it('replaces browser DPI metadata instead of adding a conflicting value', () => {
    const result = chunks(setPngDpi(setPngDpi(png, 96), 600))
    const resolutions = result.filter((chunk) => chunk.kind === 'pHYs')
    expect(resolutions).toHaveLength(1)
    expect(resolutions[0].data.readUInt32BE(0) * 0.0254).toBeCloseTo(600, 1)
  })

  it('rejects invalid image data and invalid DPI', () => {
    expect(() => setPngDpi(new Uint8Array(), 300)).toThrow()
    expect(() => setPngDpi(png.subarray(0, 18), 300)).toThrow()
    expect(() => setPngDpi(png, 0)).toThrow()
    expect(() => setPngDpi(png, NaN)).toThrow()
  })
})
