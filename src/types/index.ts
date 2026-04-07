import { ObservationRecord } from '@uwrl/qc-utils'

export type EnumDictionary<T extends string | symbol | number, U> = {
  [K in T]: U
}

export interface GraphSeries {
  id: string
  name: string
  data: ObservationRecord
  yAxisLabel: string
}
