import {
  Datastream,
  ObservedProperty,
  ProcessingLevel,
  Thing,
} from '@hydroserver/client'

const apiHost = import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''
const apiBaseUrl = import.meta.env.VITE_APP_PROXY_BASE_URL || apiHost

interface VisualizationThingPayload {
  id: string
  workspaceId: string
  name: string
  samplingFeatureCode: string
}

interface VisualizationObservedPropertyPayload {
  id: string
  name: string
  code: string
}

interface VisualizationProcessingLevelPayload {
  id: string
  definition?: string | null
}

interface VisualizationDatastreamPayload {
  id: string
  name: string
  thingId: string
  observedPropertyId: string
  processingLevelId: string
  unitId: string
  noDataValue: number
  valueCount?: number | null
  phenomenonBeginTime?: string | null
  phenomenonEndTime?: string | null
  intendedTimeSpacing?: number
  intendedTimeSpacingUnit?: 'seconds' | 'minutes' | 'hours' | 'days' | null
}

interface VisualizationBootstrapPayload {
  things: VisualizationThingPayload[]
  datastreams: VisualizationDatastreamPayload[]
  observedProperties: VisualizationObservedPropertyPayload[]
  processingLevels: VisualizationProcessingLevelPayload[]
}

export async function getVisualizationBootstrap() {
  const response = await fetch(
    `${apiBaseUrl}/api/data/datastreams/visualization-bootstrap`,
    {
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to load visualization bootstrap: ${response.status}`)
  }

  const payload = (await response.json()) as VisualizationBootstrapPayload

  const things = payload.things.map((thingPayload) =>
    Object.assign(new Thing(), thingPayload)
  )
  const thingById = new Map(things.map((thing) => [thing.id, thing]))

  const datastreams = payload.datastreams.map((datastreamPayload) =>
    Object.assign(new Datastream(), {
      ...datastreamPayload,
      workspaceId: thingById.get(datastreamPayload.thingId)?.workspaceId ?? '',
    })
  )
  const observedProperties = payload.observedProperties.map(
    (observedPropertyPayload) =>
      Object.assign(new ObservedProperty(), observedPropertyPayload)
  )
  const processingLevels = payload.processingLevels.map(
    (processingLevelPayload) =>
      Object.assign(new ProcessingLevel(), processingLevelPayload)
  )

  return {
    things,
    datastreams,
    observedProperties,
    processingLevels,
  }
}
