import type { Datastream } from '@hydroserver/client'

// App-side extensions until #630 defines the generated API contracts.
export type ProfileDatastream = Omit<Datastream, 'type'> & {
  type: 'profileCoverage'
  zReference?: string
  zUnit?: string
}
export const datastreamTypeOptions = ['Time Series', 'Profile', 'Discrete']
export function isProfileDatastream(stream: { type?: string }) {
  return stream.type === 'profileCoverage'
}
export function datastreamTypeLabel(stream: { type?: string }) {
  if (isProfileDatastream(stream)) return 'Profile'
  if (
    stream.type === 'discrete' ||
    stream.type === 'discreteCoverage' ||
    stream.type === 'qualitySample'
  )
    return 'Discrete'
  return stream.type === 'timeSeriesCoverage' || !stream.type
    ? 'Time Series'
    : stream.type
}
export type ProfileVisit = {
  phenomenonTime: string
  label: string
  status: 'sensor only' | 'lab confirmed' | 'lab pending'
}
export type ProfileAnalyte = {
  datastreamId: string
  name: string
  unit: string
}
export type ProfileObservation = {
  datastreamId: string
  phenomenonTime: string
  z: number
  result: number | null
}
export type ProfileData = {
  zReference: string
  zUnit: string
  positiveDirection: 'down' | 'up'
  visits: ProfileVisit[]
  analytes: ProfileAnalyte[]
  observations: ProfileObservation[]
}
export function profilePoints(data: ProfileData, id: string, time: string) {
  return data.observations
    .filter(
      (point) =>
        point.datastreamId === id &&
        point.phenomenonTime === time &&
        Number.isFinite(point.z)
    )
    .map((point) => ({
      ...point,
      result:
        point.result !== null && Number.isFinite(point.result)
          ? point.result
          : null,
    }))
    .sort((a, b) => a.z - b.z)
}
export function hasProfileValues(data: ProfileData, id: string, time: string) {
  return profilePoints(data, id, time).some((point) => point.result !== null)
}
/** Profile selection is exclusive; time series retain their existing five-series limit. */
export function selectPlotDatastream(
  current: Datastream[],
  stream: Datastream,
  selected: boolean
) {
  if (!selected) return current.filter((item) => item.id !== stream.id)
  if (isProfileDatastream(stream)) return [stream]
  const compatible = current.filter((item) => !isProfileDatastream(item))
  if (
    compatible.some((item) => item.id === stream.id) ||
    compatible.length >= 5
  )
    return compatible
  return [...compatible, stream]
}
