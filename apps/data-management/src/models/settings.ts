export interface Provider {
  id: string
  name: string
  iconLink: string | null
  signupEnabled: boolean
  connectEnabled: boolean
}

interface AuthenticationConfiguration {
  hydroserverSignupEnabled: boolean
  providers: Provider[]
}

interface ContactOption {
  title: string
  text: string | null
  action: string | null
  icon: string | null
  link: string | null
}

interface AboutInformation {
  showAboutInformation: boolean
  title: string | null
  text: string | null
  contactOptions: ContactOption[]
}

export enum ElevationService {
  OpenElevation = 'openElevation',
  Google = 'google',
}

export enum GeoService {
  Nominatim = 'nominatim',
  Google = 'google',
}

interface MapLayer {
  name: string
  source: string
  attribution: string
  priority?: number | null
}

interface MapConfiguration {
  defaultLatitude: number
  defaultLongitude: number
  defaultZoomLevel: number
  defaultBaseLayer: string
  defaultSatelliteLayer: string
  elevationService: ElevationService
  geoService: GeoService
  basemapLayers: MapLayer[]
  overlayLayers: MapLayer[]
}

interface AnalyticsConfiguration {
  enableClarityAnalytics: boolean
  clarityProjectId?: string | null
}

interface LegalInformation {
  termsOfUseLink?: string | null
  privacyPolicyLink?: string | null
  copyright?: string | null
}

export interface AppSettings {
  authenticationConfiguration: AuthenticationConfiguration
  aboutInformation: AboutInformation
  mapConfiguration: MapConfiguration
  analyticsConfiguration: AnalyticsConfiguration
  legalInformation: LegalInformation
}
