import { MonitoringSite, MonitoringSiteMarker, MonitoringSiteMapSummary } from '@hydroserver/client'

export type { MonitoringSiteMarker, MonitoringSiteMapSummary }

export type MapMonitoringSite = MonitoringSite | MonitoringSiteMarker | MonitoringSiteMapSummary

interface MonitoringSiteWithColor extends MonitoringSite {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

export interface MonitoringSiteMapSummaryWithColor extends MonitoringSiteMapSummary {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

interface MonitoringSiteMarkerWithColor extends MonitoringSiteMarker {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

export type MapMonitoringSiteWithColor =
  | MonitoringSiteWithColor
  | MonitoringSiteMarkerWithColor
  | MonitoringSiteMapSummaryWithColor
