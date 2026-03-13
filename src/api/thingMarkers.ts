import type { ThingMarker } from '@/types'

const apiHost = import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''

export async function listThingMarkers(): Promise<ThingMarker[]> {
  const response = await fetch(`${apiHost}/api/data/things/markers`, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to load thing markers: ${response.status}`)
  }

  return (await response.json()) as ThingMarker[]
}
