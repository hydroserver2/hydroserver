import {
  EnumEditOperations,
  ObservationRecord,
} from "@uwrl/qc-utils"

export type EnumDictionary<T extends string | symbol | number, U> = {
  [K in T]: U
}

export type HistoryItem = {
  method: EnumEditOperations
  icon: string
  isLoading: boolean
  args?: any[]
  duration?: number
  status?: 'success' | 'failed'
}

export type DataPoint = {
  date: Date
  value: number
}

export type DataArray = [string, number][]

export interface GraphSeries {
  id: string
  name: string
  data: ObservationRecord
  yAxisLabel: string
  seriesOption: any
}