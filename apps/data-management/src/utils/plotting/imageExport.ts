export type FigureExportTarget =
  | { mode: 'screen'; scale: number }
  | { mode: 'print'; widthInches: number; heightInches: number; dpi: number }

/** Convert physical print dimensions or screen scaling to output pixels. */
export function getFigureExportSize(
  width: number,
  height: number,
  target: FigureExportTarget
) {
  const scale =
    target.mode === 'print'
      ? Math.round(target.widthInches * target.dpi) / width
      : target.scale
  return {
    width:
      target.mode === 'print'
        ? Math.round(target.widthInches * target.dpi)
        : Math.floor(width * scale),
    height:
      target.mode === 'print'
        ? Math.round(target.heightInches * target.dpi)
        : Math.floor(height * scale),
    scale,
    dpi: target.mode === 'print' ? target.dpi : 96,
  }
}

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff
  for (const byte of bytes) {
    crc ^= byte
    for (let bit = 0; bit < 8; bit++) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0)
    }
  }
  return (crc ^ 0xffffffff) >>> 0
}

/** Set PNG print-size metadata without resampling or changing image content. */
export function setPngDpi(png: Uint8Array, dpi: number) {
  const signature = [137, 80, 78, 71, 13, 10, 26, 10]
  if (
    !Number.isFinite(dpi) ||
    dpi <= 0 ||
    !signature.every((byte, index) => png[index] === byte)
  ) {
    throw new Error('A PNG image and a positive DPI are required.')
  }

  const resolution = new Uint8Array(21)
  const view = new DataView(resolution.buffer)
  view.setUint32(0, 9)
  resolution.set([112, 72, 89, 115], 4) // pHYs
  const pixelsPerMetre = Math.round(dpi / 0.0254)
  view.setUint32(8, pixelsPerMetre)
  view.setUint32(12, pixelsPerMetre)
  resolution[16] = 1 // metres
  view.setUint32(17, crc32(resolution.subarray(4, 17)))

  const parts = [png.subarray(0, 8)]
  let inserted = false
  for (let offset = 8; offset < png.length;) {
    if (offset + 12 > png.length) throw new Error('Invalid PNG chunk.')
    const length = new DataView(
      png.buffer,
      png.byteOffset + offset,
      4
    ).getUint32(0)
    const end = offset + length + 12
    if (end > png.length) throw new Error('Invalid PNG chunk length.')
    const kind = String.fromCharCode(...png.subarray(offset + 4, offset + 8))
    if (kind !== 'pHYs') parts.push(png.subarray(offset, end))
    if (kind === 'IHDR') {
      parts.push(resolution)
      inserted = true
    }
    offset = end
  }
  if (!inserted) throw new Error('PNG image header is missing.')
  const result = new Uint8Array(
    parts.reduce((length, part) => length + part.length, 0)
  )
  let offset = 0
  for (const part of parts) {
    result.set(part, offset)
    offset += part.length
  }
  return result
}
