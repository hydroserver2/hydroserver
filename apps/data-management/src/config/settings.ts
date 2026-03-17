import { AppSettings, ElevationService, GeoService } from '@/models/settings'

const devHost = import.meta.env.VITE_APP_PROXY_BASE_URL || 'http://127.0.0.1:8000'
const defaultSettings: AppSettings = {
  authenticationConfiguration: {
    hydroserverSignupEnabled: false,
    providers: [],
  },
  aboutInformation: {
    showAboutInformation: false,
    title: null,
    text: null,
    contactOptions: [],
  },
  mapConfiguration: {
    defaultLatitude: 0,
    defaultLongitude: 0,
    defaultZoomLevel: 2,
    defaultBaseLayer: '',
    defaultSatelliteLayer: '',
    elevationService: ElevationService.OpenElevation,
    geoService: GeoService.Nominatim,
    basemapLayers: [],
    overlayLayers: [],
  },
  analyticsConfiguration: {
    enableClarityAnalytics: false,
    clarityProjectId: null,
  },
  legalInformation: {
    termsOfUseLink: null,
    privacyPolicyLink: null,
    copyright: null,
  },
}

let scriptTag: HTMLScriptElement | null

if (import.meta.env.DEV) {
  const xhr = new XMLHttpRequest()
  xhr.open('GET', devHost, false)
  xhr.send(null)
  const indexHtml = xhr.status >= 200 && xhr.status < 300 ? xhr.responseText : null
  const parser = new DOMParser()
  const doc = indexHtml
    ? parser.parseFromString(indexHtml, 'text/html')
    : document.implementation.createHTMLDocument('')
  scriptTag = doc.getElementById('app-settings') as HTMLScriptElement
} else {
  scriptTag = document.getElementById('app-settings') as HTMLScriptElement
}

function parseSettings(): Partial<AppSettings> {
  if (!scriptTag?.textContent) return {}

  try {
    return JSON.parse(scriptTag.textContent) as Partial<AppSettings>
  } catch (error) {
    console.error('Failed to parse app settings', error)
    return {}
  }
}

const parsedSettings = parseSettings()

export const settings: AppSettings = {
  ...defaultSettings,
  ...parsedSettings,
  authenticationConfiguration: {
    ...defaultSettings.authenticationConfiguration,
    ...parsedSettings.authenticationConfiguration,
  },
  aboutInformation: {
    ...defaultSettings.aboutInformation,
    ...parsedSettings.aboutInformation,
  },
  mapConfiguration: {
    ...defaultSettings.mapConfiguration,
    ...parsedSettings.mapConfiguration,
  },
  analyticsConfiguration: {
    ...defaultSettings.analyticsConfiguration,
    ...parsedSettings.analyticsConfiguration,
  },
  legalInformation: {
    ...defaultSettings.legalInformation,
    ...parsedSettings.legalInformation,
  },
}
