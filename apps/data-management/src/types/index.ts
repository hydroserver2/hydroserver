import { Thing, ThingMarker, ThingSiteSummary } from '@hydroserver/client'

export type { ThingMarker, ThingSiteSummary }

export type MapThing = Thing | ThingMarker | ThingSiteSummary

interface ThingWithColor extends Thing {
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

interface ThingMarkerWithColor extends ThingMarker {
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
