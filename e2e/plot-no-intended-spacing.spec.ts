/**
 * Plotting policy for datastreams without a declared `intendedTimeSpacing`.
 *
 * Two related guarantees, both covered here:
 *   1. The main trace renders as a pure scatter — `mode: 'markers'` with
 *      no companion `_gapOverlayFor` lines trace pushed alongside it.
 *   2. The "data points" toggle (manual mode + click off) does not hide
 *      the markers of such a series. Without a line fallback, honouring
 *      the toggle would leave the series invisible, so the relayout
 *      pipeline must pin its marker opacity at 1 regardless of toggle
 *      state.
 *
 * The fixture datastream ships with `intendedTimeSpacing: 15`. We
 * stack a more-specific `page.route` on top of `installMocks` so the
 * server response for both the list and single-get endpoints arrives
 * with that field cleared.
 */

import { expect, test, type Page, type Route } from '@playwright/test'
import { installMocks } from './support/mocks'
import { datastreams, DATASTREAM_ID } from './support/fixtures'
import { setupEditView } from './support/app'

type DatastreamRecord = (typeof datastreams)[number]
type RoutedTrace = {
  id?: string
  mode?: string
  marker?: { opacity?: number }
  _isGapOverlay?: boolean
  _gapOverlayFor?: string
}

/**
 * Poll the live plot until Plotly has rendered a trace for the
 * targeted datastream id. `plotDatastreamById` only waits for the
 * loading indicator; the trace itself lands a frame later when
 * `Plotly.react` resolves.
 */
async function waitForTraceRendered(page: Page, id: string): Promise<void> {
  await page.waitForFunction(
    (targetId) => {
      const gd = document.querySelector('.plot-main') as
        | (HTMLElement & { data?: Array<{ id?: string }> })
        | null
      return !!gd?.data?.some((t) => t.id === targetId)
    },
    id,
    { timeout: 15_000 }
  )
}

function withoutIntendedSpacing(ds: DatastreamRecord): DatastreamRecord {
  // Mirror what the backend serves for an older / minimally-configured
  // datastream: both spacing fields cleared. The QC app's
  // `spacingMsFromDatastream` returns null for either missing field, so
  // wiping the unit alone would already trip the scatter path — clearing
  // both keeps the fixture honest about the upstream shape.
  return { ...ds, intendedTimeSpacing: null, intendedTimeSpacingUnit: null }
}

async function patchDatastreamFixture(route: Route): Promise<void> {
  const request = route.request()
  if (request.method() !== 'GET') return route.fallback()
  const origin = request.headers()['origin'] ?? '*'
  const path = new URL(request.url()).pathname
  // Mirror the CORS + pagination headers `installMocks` sets so the
  // HydroServer client treats our patched responses exactly the same
  // as the base mocks. Dropping `Access-Control-Expose-Headers` made
  // some clients trip on missing `X-Total-Pages`.
  const headers: Record<string, string> = {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Expose-Headers': 'X-Total-Pages,X-Total-Count',
    'X-Total-Pages': '1',
  }
  if (/\/api\/data\/datastreams$/.test(path)) {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers,
      body: JSON.stringify({ data: datastreams.map(withoutIntendedSpacing) }),
    })
  }
  const single = path.match(/\/api\/data\/datastreams\/([^/]+)$/)
  if (single) {
    const id = single[1]
    const ds = datastreams.find((d) => d.id === id) ?? datastreams[0]!
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers,
      body: JSON.stringify({ data: withoutIntendedSpacing(ds) }),
    })
  }
  return route.fallback()
}

test.describe('plot: datastream without intendedTimeSpacing', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    // Routes added with `page.route` are invoked LIFO, so this stack
    // sits on top of the catch-all installed by `installMocks` and
    // wins for both the list and single-get endpoints. The sub-path
    // `/observations` is left to fall through.
    await page.route(
      /\/api\/data\/datastreams(\/[^/]+)?(\?.*)?$/,
      patchDatastreamFixture
    )
  })

  test('renders as a pure scatter (markers only, no gap-overlay line)', async ({
    page,
  }) => {
    await setupEditView(page)
    await waitForTraceRendered(page, DATASTREAM_ID)

    const trace = await page.evaluate((id) => {
      const gd = document.querySelector('.plot-main') as
        | (HTMLElement & { data?: RoutedTrace[] })
        | null
      const traces = gd?.data ?? []
      const main = traces.find((t) => t.id === id) ?? null
      const overlay = traces.find((t) => t._gapOverlayFor === id) ?? null
      return {
        mainMode: main?.mode ?? null,
        mainMarkerOpacity: main?.marker?.opacity ?? null,
        overlayExists: !!overlay,
        // Sanity: there should also be no `mode: 'lines'` trace
        // pointing at this series via the gap-overlay channel. The
        // app reserves `_gapOverlayFor` exclusively for that role,
        // so its absence is the precise signal.
        anyGapOverlay: traces.some((t) => t._gapOverlayFor === id),
      }
    }, DATASTREAM_ID)

    expect(trace.mainMode).toBe('markers')
    expect(trace.overlayExists).toBe(false)
    expect(trace.anyGapOverlay).toBe(false)
    // Initial paint must keep the scatter markers fully opaque —
    // otherwise the series has nothing visible on screen.
    expect(trace.mainMarkerOpacity).toBe(1)
  })

  test('ignores the data-points toggle (markers stay visible after switching off)', async ({
    page,
  }) => {
    await setupEditView(page)
    await waitForTraceRendered(page, DATASTREAM_ID)

    // The toggle button only renders in manual mode; default is auto,
    // so open the dropdown and pick manual first. Picking manual also
    // fires `handleRelayout(null)` internally — that pass is the one
    // that would have wiped the markers if the scatter exemption were
    // missing.
    await page.getByTestId('tooltips-mode-btn').click()
    await page.getByTestId('tooltips-mode-manual').click()

    const toggle = page.getByTestId('tooltips-toggle-btn')
    await expect(toggle).toBeVisible()
    // `tooltipsManualEnabled` defaults to true, so the first click is
    // the off-flip we want to verify.
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'false')

    // `toggleTooltips` calls `handleRelayout(null)` synchronously; the
    // debounced body schedules a microtask + setTimeout(0), so give
    // the next opacity-restyle pass a tick to land.
    await page.waitForTimeout(150)

    const main = await page.evaluate((id) => {
      const gd = document.querySelector('.plot-main') as
        | (HTMLElement & { data?: RoutedTrace[] })
        | null
      const t = gd?.data?.find((tr) => tr.id === id)
      return t ? { opacity: t.marker?.opacity ?? null } : null
    }, DATASTREAM_ID)

    expect(main).not.toBeNull()
    // Scatter-only series ignore the toggle: markers stay fully opaque.
    expect(main!.opacity).toBe(1)
  })
})
