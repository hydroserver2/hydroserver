import type { Datastream } from '@hydroserver/client'

export function datastreamThingId(datastream: Datastream): string {
  const expandedThingId = (datastream as Datastream & { thing?: { id?: string } })
    .thing?.id
  return datastream.thingId || expandedThingId || ''
}

export function datastreamsForThing(
  datastreams: Datastream[],
  thingId: string | null | undefined
) {
  if (!thingId) return []
  return datastreams.filter((datastream) => datastreamThingId(datastream) === thingId)
}
