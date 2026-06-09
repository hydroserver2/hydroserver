export type RatingCurveFittingMethod = 'linear' | 'power_law'
export type RatingCurvePoint = [number, number]

export class RatingCurve {
  id = ''
  name = ''
  description: string | null = null
  fittingMethod: RatingCurveFittingMethod = 'linear'
  thingId = ''
  thing?: { id: string; name: string; [key: string]: unknown }
  points: RatingCurvePoint[] = []

  constructor(init?: Partial<RatingCurve>) {
    Object.assign(this, init)
    if (!this.thingId && this.thing?.id) this.thingId = this.thing.id
  }
}
