export type RatingCurveFittingMethod = 'linear' | 'power_law'
export type RatingCurvePoint = [number, number]

export class RatingCurve {
  id = ''
  name = ''
  description: string | null = null
  fittingMethod: RatingCurveFittingMethod = 'linear'
  monitoringSiteId = ''
  monitoringSite?: { id: string; name: string; [key: string]: unknown }
  points: RatingCurvePoint[] = []

  constructor(init?: Partial<RatingCurve>) {
    Object.assign(this, init)
    if (!this.monitoringSiteId && this.monitoringSite?.id) this.monitoringSiteId = this.monitoringSite.id
  }
}
