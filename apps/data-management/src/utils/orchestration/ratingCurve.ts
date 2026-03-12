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
