import { Thing } from '@hydroserver/client'

export interface ThingTag {
  key: string
  value: string
}

export interface ThingMarker {
  id: string
  workspaceId: string
  name: string
  siteType: string
  isPrivate: boolean
  latitude: number
  longitude: number
}

export interface ThingSiteSummary extends ThingMarker {
  samplingFeatureCode: string
  tags: ThingTag[]
}

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
