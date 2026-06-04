import { Thing, ThingMarker, ThingSiteSummary } from '@hydroserver/client'

export type { ThingMarker, ThingSiteSummary }

export type MapThing = Thing | ThingMarker | ThingSiteSummary

export interface ThingWithColor extends Thing {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

export interface ThingSiteSummaryWithColor extends ThingSiteSummary {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

export interface ThingMarkerWithColor extends ThingMarker {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

export type MapThingWithColor =
  | ThingWithColor
  | ThingMarkerWithColor
  | ThingSiteSummaryWithColor
