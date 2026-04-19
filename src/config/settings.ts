import type { AppSettings } from '@/models/settings'

/**
 * Runtime app settings injected by the backend. In prod this file is
 * served by the HydroServer host itself, so the index HTML already
 * ships an `<script id="app-settings" type="application/json">` with
 * the auth provider list, map config, etc. — we just parse it.
 *
 * In dev the qc-app runs under Vite at a different origin than the
 * backend (`VITE_APP_API_URL`, typically `https://playground.hydroserver.org`).
 * The backend's anonymous `/api/auth/browser/session` response does
 * not include the provider list (it ships in the index HTML instead),
 * so we fetch the backend's root HTML once at boot and pull the
 * script tag out of that.
 *
 * `loadAppSettings()` must be awaited from `main.ts` before `app.mount`
 * so the OAuth buttons (and any other settings-driven UI) render with
 * the correct config on the first paint.
 */

const EMPTY_SETTINGS: AppSettings = {
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
    defaultZoomLevel: 1,
    defaultBaseLayer: '',
    defaultSatelliteLayer: '',
    elevationService: 'openElevation' as unknown as AppSettings['mapConfiguration']['elevationService'],
    geoService: 'nominatim' as unknown as AppSettings['mapConfiguration']['geoService'],
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

export let settings: AppSettings = EMPTY_SETTINGS

function parseSettings(textContent: string | null | undefined): AppSettings | null {
  if (!textContent) return null
  try {
    return JSON.parse(textContent) as AppSettings
  } catch {
    return null
  }
}

function readInlineSettings(): AppSettings | null {
  const tag = document.getElementById('app-settings') as HTMLScriptElement | null
  return parseSettings(tag?.textContent)
}

async function fetchRemoteSettings(apiUrl: string): Promise<AppSettings | null> {
  try {
    const res = await fetch(apiUrl, { credentials: 'omit' })
    if (!res.ok) return null
    const html = await res.text()
    const doc = new DOMParser().parseFromString(html, 'text/html')
    const tag = doc.getElementById('app-settings') as HTMLScriptElement | null
    return parseSettings(tag?.textContent)
  } catch (err) {
    console.warn('Failed to fetch app settings from backend', err)
    return null
  }
}

export async function loadAppSettings(): Promise<AppSettings> {
  const inline = readInlineSettings()
  if (inline) {
    settings = inline
    return inline
  }

  const apiUrl = import.meta.env.VITE_APP_API_URL as string | undefined
  if (apiUrl) {
    const remote = await fetchRemoteSettings(apiUrl)
    if (remote) {
      settings = remote
      return remote
    }
  }

  settings = EMPTY_SETTINGS
  return EMPTY_SETTINGS
}
