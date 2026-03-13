import { Thing } from '@hydroserver/client'

export interface ThingMarker {
  id: string
  workspaceId: string
  name: string
  siteType: string
  isPrivate: boolean
  latitude: number
  longitude: number
}

export type MapThing = Thing | ThingMarker

export interface ThingWithColor extends Thing {
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

export type MapThingWithColor = ThingWithColor | ThingMarkerWithColor
