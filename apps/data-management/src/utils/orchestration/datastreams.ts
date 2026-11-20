import type { Datastream } from '@hydroserver/client'

export function datastreamMonitoringSiteId(datastream: Datastream): string {
  const ds = datastream as Datastream & {
    monitoringSite?: { id?: string }
    monitoring_site_id?: string
  }
  return datastream.monitoringSiteId || ds.monitoring_site_id || ds.monitoringSite?.id || ''
}

export function datastreamsForMonitoringSite(
  datastreams: Datastream[],
  monitoringSiteId: string | null | undefined
) {
  if (!monitoringSiteId) return []
  return datastreams.filter(
    (datastream) => datastreamMonitoringSiteId(datastream) === monitoringSiteId
  )
}
