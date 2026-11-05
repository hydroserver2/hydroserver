import type { ProfileData } from '@/models/profile'

// Provisional read endpoint. The demo Vite plugin serves the same contract;
// replace this adapter when the backend's profile queries are finalized.
export async function fetchProfileData(
  datastreamId: string,
  signal?: AbortSignal
): Promise<ProfileData> {
  const response = await fetch(
    `/api/ogc/collections/datastreams/items/${encodeURIComponent(datastreamId)}/profiles`,
    {
      credentials: 'same-origin',
      signal,
    }
  )
  if (!response.ok)
    throw new Error(`Unable to load profiles (${response.status}).`)
  const data: ProfileData = await response.json()
  if (
    !Array.isArray(data.visits) ||
    !Array.isArray(data.analytes) ||
    !Array.isArray(data.observations)
  ) {
    throw new Error('The profile response is incomplete.')
  }
  return data
}
