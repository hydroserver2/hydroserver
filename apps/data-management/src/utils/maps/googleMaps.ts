import { Loader } from '@googlemaps/js-api-loader'

interface GoogleGeocodeResponse {
  status: string
  results: Array<{
    address_components: Array<{
      long_name: string
      types: string[]
    }>
  }>
}

let googleMapsPromise: Promise<typeof google.maps.Map> | null = null

export function loadGoogleMapsApi(): Promise<typeof google.maps.Map> {
  if (googleMapsPromise) return googleMapsPromise
  const loader = new Loader({
    apiKey: import.meta.env.VITE_APP_GOOGLE_MAPS_API_KEY,
    version: 'weekly',
    libraries: ['places'],
  })
  googleMapsPromise = (async () => {
    const { Map } = await loader.importLibrary('maps')
    return Map
  })()
  return googleMapsPromise
}

export async function getElevationGoogle(latitude: number, longitude: number) {
  const Map = await loadGoogleMapsApi()
  const elevator = new google.maps.ElevationService()
  const { results } = await elevator.getElevationForLocations({
    locations: [{ lat: latitude, lng: longitude }],
  })
  if (!results[0]) throw new Error('No elevation found')
  return results[0].elevation
}

function parseGoogleAddress(response: GoogleGeocodeResponse) {
  if (response.status !== 'OK' || response.results.length === 0) {
    throw new Error(`Google Geocoding API error: ${response.status}`)
  }

  const { adminArea1, adminArea2, country } =
    response.results[0].address_components.reduce(
      (acc: any, component: any) => {
        if (component.types.includes('administrative_area_level_1'))
          acc.adminArea1 = component.short_name
        if (component.types.includes('administrative_area_level_2'))
          acc.adminArea2 = component.short_name
        if (component.types.includes('country'))
          acc.country = component.short_name
        return acc
      },
      { adminArea1: '', adminArea2: '', country: '' }
    )

  return { adminArea1, adminArea2, country }
}

export async function getGeoDataGoogle(latitude: number, longitude: number) {
  if (!import.meta.env.VITE_APP_GOOGLE_MAPS_API_KEY)
    throw new Error('Missing Google Maps API key')
  const url = new URL('https://maps.googleapis.com/maps/api/geocode/json')
  url.searchParams.set('latlng', `${latitude},${longitude}`)
  url.searchParams.set('key', import.meta.env.VITE_APP_GOOGLE_MAPS_API_KEY)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Google Geocoding HTTP error: ${res.status}`)
  const data = (await res.json()) as GoogleGeocodeResponse
  return parseGoogleAddress(data)
}
