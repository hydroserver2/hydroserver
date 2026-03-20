export function getRatingCurveReference(transformation: any): string {
  if (!transformation || transformation.type !== 'rating_curve') return ''

  const ratingCurveUrl = transformation.ratingCurveUrl
  return typeof ratingCurveUrl === 'string' ? ratingCurveUrl.trim() : ''
}

export function setRatingCurveReference(
  transformation: any,
  reference: string
): void {
  const normalized = (reference || '').trim()
  transformation.ratingCurveUrl = normalized
}

type ParsedRatingCurveReference = {
  raw: string
  pathname: string
  attachmentId: string
  thingId: string
  filename: string
}

export function parseRatingCurveReference(value: string): ParsedRatingCurveReference {
  const raw = `${value ?? ''}`.trim().replace(/\/+$/, '')
  if (!raw) {
    return {
      raw: '',
      pathname: '',
      attachmentId: '',
      thingId: '',
      filename: '',
    }
  }

  try {
    const parsed = new URL(raw, globalThis.location?.origin ?? undefined)
    const pathname = parsed.pathname.replace(/\/+$/, '')
    return {
      raw,
      pathname,
      attachmentId: extractAttachmentId(pathname),
      thingId: extractThingId(pathname),
      filename: extractFilename(pathname),
    }
  } catch {
    const pathname = raw.replace(/\/+$/, '')
    return {
      raw,
      pathname,
      attachmentId: extractAttachmentId(pathname),
      thingId: extractThingId(pathname),
      filename: extractFilename(pathname),
    }
  }
}

export function isSameRatingCurveReference(left: string, right: string): boolean {
  const leftRef = parseRatingCurveReference(left)
  const rightRef = parseRatingCurveReference(right)

  if (leftRef.raw && rightRef.raw && leftRef.raw === rightRef.raw) return true
  if (
    leftRef.pathname &&
    rightRef.pathname &&
    leftRef.pathname === rightRef.pathname
  ) {
    return true
  }
  if (
    leftRef.attachmentId &&
    rightRef.attachmentId &&
    leftRef.attachmentId === rightRef.attachmentId
  ) {
    return true
  }
  if (
    leftRef.thingId &&
    rightRef.thingId &&
    leftRef.filename &&
    rightRef.filename &&
    leftRef.thingId === rightRef.thingId &&
    leftRef.filename === rightRef.filename
  ) {
    return true
  }

  return false
}

function extractAttachmentId(path: string): string {
  const match =
    /\/things\/[^/]+\/file-attachments\/([^/]+)\/download\/?$/i.exec(path)
  if (!match?.[1]) return ''
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

function extractThingId(path: string): string {
  const match = /\/things\/([^/]+)\/file-attachments\/[^/]+\/download\/?$/i.exec(
    path
  )
  const mediaMatch = /\/media\/things\/([^/]+)\/[^/]+$/i.exec(path)
  const value = match?.[1] || mediaMatch?.[1]
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function extractFilename(path: string): string {
  const apiMatch =
    /\/things\/[^/]+\/file-attachments\/([^/]+)\/download\/?$/i.exec(path)
  const mediaMatch = /\/media\/things\/[^/]+\/([^/]+)$/i.exec(path)
  const value = apiMatch?.[1] || mediaMatch?.[1]
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}
