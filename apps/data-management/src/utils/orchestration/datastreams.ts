import type { Datastream } from '@hydroserver/client'

export function datastreamThingId(datastream: Datastream): string {
  const ds = datastream as Datastream & {
    thing?: { id?: string }
    thing_id?: string
  }
  return datastream.thingId || ds.thing_id || ds.thing?.id || ''
}

export function datastreamsForThing(
  datastreams: Datastream[],
  thingId: string | null | undefined
) {
  if (!thingId) return []
  return datastreams.filter(
    (datastream) => datastreamThingId(datastream) === thingId
  )
}
