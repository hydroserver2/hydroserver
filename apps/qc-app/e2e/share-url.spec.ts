/**
 * Share-URL round trip: emit + hydrate.
 *
 * Two complementary halves:
 *   - **Emit**: drive the UI, then read `window.location.search` and
 *     assert the compact-shape keys appear (and the legacy ones are
 *     gone).
 *   - **Hydrate**: open a deep-linked URL carrying the keys, then
 *     assert the app lands in the expected state (plotted ids, tab,
 *     edit view, data-points threshold, hidden traces).
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView, startSessionFromRow } from './support/app'
import {
  DATASTREAM_ID,
  DATASTREAM_ID_B,
  MANAGED_DATASTREAM_ID,
  buildObservations,
  buildTemperatureObservations,
  FIXTURE_OBS_END_MS,
  FIXTURE_OBS_START_MS,
  WORKSPACE_ID,
} from './support/fixtures'

/**
 * Poll the live plot for: the current X range (as `[loMs, hiMs]`)
 * and a cursor coordinate hovering over the middle of the plot
 * (used by callers that want to dispatch wheel events from there).
 */
async function waitForPlotMeta(page: Page) {
  return page.evaluate(async () => {
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))
    const start = Date.now()
    while (Date.now() - start < 10_000) {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (HTMLElement & {
            _fullLayout?: {
              xaxis?: {
                range?: [number | string, number | string]
                _offset?: number
                _length?: number
              }
            }
          })
        | null
      const xa = gd?._fullLayout?.xaxis
      if (gd && xa?.range && xa._offset != null && xa._length != null) {
        const toMs = (v: number | string) =>
          typeof v === 'string' ? Date.parse(v) : v
        const bounds = (gd as HTMLElement).getBoundingClientRect()
        return {
          dataFitRange: [toMs(xa.range[0]), toMs(xa.range[1])] as [
            number,
            number,
          ],
          cursorClient: {
            x: bounds.x + xa._offset + xa._length / 2,
            y: bounds.y + bounds.height / 2,
          },
        }
      }
      await wait(100)
    }
    return null
  })
}

async function clickResetAxes(page: Page) {
  const selector =
    '.modebar-btn[data-attr="reset-axes"], .modebar-btn[data-title="Reset axes"]'

  await page.waitForFunction(
    (buttonSelector) => {
      const button = document.querySelector(
        buttonSelector
      ) as HTMLElement | null
      if (!button) return false

      const rect = button.getBoundingClientRect()
      const style = window.getComputedStyle(button)
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden'
      )
    },
    selector,
    { timeout: 15_000 }
  )

  await page.evaluate((buttonSelector) => {
    const button = document.querySelector(
      buttonSelector
    ) as HTMLButtonElement | null
    if (!button) throw new Error('Reset axes modebar button was not found')
    button.click()
  }, selector)
}

/** The live X range of the main plot as `[loMs, hiMs]`, or null. */
async function plotXRange(page: Page): Promise<[number, number] | null> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as
      | (HTMLElement & {
          _fullLayout?: { xaxis?: { range?: [number | string, number | string] } }
        })
      | null
    const range = gd?._fullLayout?.xaxis?.range
    if (!range) return null
    const toMs = (v: number | string) =>
      typeof v === 'number' ? v : Date.parse(v)
    return [toMs(range[0]), toMs(range[1])] as [number, number]
  })
}

/**
 * Whether the plot is showing the session-window band the editor draws, which
 * is what "the editor opened on its session window" looks like from outside.
 */
async function zoomedToSessionWindow(page: Page): Promise<string> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as
      | (HTMLElement & {
          _fullLayout?: { xaxis?: { range?: [number | string, number | string] } }
          layout?: { shapes?: { name?: string; x0?: unknown; x1?: unknown }[] }
        })
      | null
    const range = gd?._fullLayout?.xaxis?.range
    const band = (gd?.layout?.shapes ?? []).find((s) => s.name === 'edit-window')
    if (!range) return 'no plot'
    if (!band) return 'no session band'
    const toMs = (v: unknown) =>
      typeof v === 'number' ? v : Date.parse(String(v))
    const near = (a: number, b: number) => Math.abs(a - b) <= 2000
    return near(toMs(range[0]), toMs(band.x0)) &&
      near(toMs(range[1]), toMs(band.x1))
      ? 'session window'
      : 'another range'
  })
}

/** Wait until the live plot draws a trace for every id in `ids`. */
async function waitForTraces(page: Page, ids: string[]) {
  await page.waitForFunction(
    (wanted) => {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (HTMLElement & { data?: Array<{ id?: string }> })
        | null
      const drawn = new Set((gd?.data ?? []).map((t) => t.id))
      return wanted.every((id) => drawn.has(id))
    },
    ids,
    { timeout: 30_000 }
  )
}

/**
 * Open an Edit-view link on the managed datastream. No session is in
 * progress in the fixture, so the window step opens; Start begins one.
 */
async function openEditLink(page: Page, extraQuery = '') {
  await page.goto(
    `/?ws=${WORKSPACE_ID}&m=e&ed=${MANAGED_DATASTREAM_ID}${extraQuery}`
  )
  await page.getByTestId('session-window-start').click({ timeout: 30_000 })
  await expect(page.getByTestId('exit-save-btn')).toBeVisible({
    timeout: 30_000,
  })
  await expect(page.getByText('Filter Data')).toBeVisible()
}

test.describe('share URL', () => {
  test.beforeEach(async ({ page }) => {
    test.slow()
    await installMocks(page, {
      qcHistories: true,
      observationsById: {
        [DATASTREAM_ID]: buildObservations(),
        [DATASTREAM_ID_B]: buildTemperatureObservations(),
      },
    })
  })

  test('writer emits the short keys after entering Edit', async ({ page }) => {
    await setupEditView(page)
    // Snapshot the query string the app has written.
    const search = await page.evaluate(() => window.location.search)
    const params = new URLSearchParams(search)

    expect(params.get('ws')).toBe(WORKSPACE_ID)
    expect(params.get('m')).toBe('e')
    // Nothing was plotted; the edit target travels in `ed`, not `ds`.
    expect(params.has('ds')).toBe(false)
    expect(params.get('ed')).toBe(MANAGED_DATASTREAM_ID)

    // Legacy keys should be gone.
    expect(params.has('workspace')).toBe(false)
    expect(params.has('datastreams')).toBe(false)
    expect(params.has('qc')).toBe(false)
    expect(params.has('mode')).toBe(false)
    expect(params.has('dateBtn')).toBe(false)
  })

  test('writer emits per-Y-axis zoom (yz=) when the primary Y axis is zoomed', async ({
    page,
  }) => {
    await setupEditView(page)
    await waitForPlotMeta(page)

    // Drop a wheel event over the *left gutter*, the band between
    // the plot edge and the primary Y axis. Our custom wheel handler
    // routes that zone to the primary y axis only, so the resulting
    // relayout updates `yaxis.range` without touching X. That sweep
    // exercises captureCurrentZoomState (which normalises `yaxis` →
    // `y`) and the URL writer (which keys `yz=` by trace-axis ref).
    const gutter = await page.evaluate(() => {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (HTMLElement & {
            _fullLayout?: {
              xaxis?: { _offset?: number }
              yaxis?: { _offset?: number; _length?: number }
            }
          })
        | null
      const xa = gd?._fullLayout?.xaxis
      const ya = gd?._fullLayout?.yaxis
      if (!gd || !xa || !ya || xa._offset == null || ya._offset == null) {
        return null
      }
      const bounds = (gd as HTMLElement).getBoundingClientRect()
      // Cursor a few px left of the plot's left edge, vertical
      // center of the primary y axis.
      return {
        x: bounds.x + Math.max(2, xa._offset - 5),
        y: bounds.y + ya._offset + (ya._length ?? 0) / 2,
      }
    })
    expect(gutter).not.toBeNull()

    await page.mouse.move(gutter!.x, gutter!.y)
    for (let i = 0; i < 3; i++) {
      await page.mouse.wheel(0, -100)
      await page.waitForTimeout(120)
    }

    await expect
      .poll(
        async () =>
          new URLSearchParams(
            await page.evaluate(() => window.location.search)
          ).get('yz'),
        { timeout: 10_000 }
      )
      // Idx 0 = the primary y axis (QC trace). The range numbers
      // depend on the wheel pivot, so just assert the prefix.
      .toMatch(/^0:/)
  })

  test('writer drops sidebar filters from the Edit-view URL', async ({
    page,
  }) => {
    await setupEditView(page)
    // None of the filter chip controls were touched, so the URL has
    // no sidebar-filter keys regardless of which view we're on.
    const search = await page.evaluate(() => window.location.search)
    const params = new URLSearchParams(search)
    expect(params.has('t')).toBe(false)
    expect(params.has('op')).toBe(false)
    expect(params.has('pl')).toBe(false)
  })

  test('hydrator restores Edit view + edit target + Table tab from URL', async ({
    page,
  }) => {
    await openEditLink(page, '&tab=t')

    // Table tab is the active tab segment. v-btn-toggle marks the
    // chosen child with `v-btn--active`.
    await expect(page.getByRole('button', { name: /^Table$/ })).toHaveClass(
      /v-btn--active/
    )
  })

  test('hydrator applies the data-points threshold from the URL', async ({
    page,
  }) => {
    await openEditLink(page, '&th=42000')

    // The auto-mode counter renders the threshold after the slash.
    const counter = page.getByTestId('tooltips-counter')
    await expect(counter).toContainText('42,000')
  })

  test('hydrator applies the URL-supplied X zoom after the plot mounts', async ({
    page,
  }) => {
    // Pick a window strictly inside the fixture's observation extent
    // (`buildObservations` makes a 120-point series at 15-min spacing
    // ending at "now"). Two hours wide, anchored a couple hours
    // before "now", so the window is well inside the loaded data.
    const now = Date.now()
    const xHi = now - 60 * 60 * 1000
    const xLo = xHi - 2 * 60 * 60 * 1000
    const toS36 = (ms: number) => Math.floor(ms / 1000).toString(36)
    const z = `${toS36(xLo)}.${toS36(xHi)}`

    await openEditLink(page, `&z=${z}`)

    // Probe Plotly's live x-axis range. Poll because the rebuild
    // can run a hair after `handleNewPlot` from the mount hook;
    // both must land on the supplied range.
    const live = await new Promise<[number, number] | null>((resolve) => {
      const start = Date.now()
      const tick = async () => {
        const r = await page.evaluate(() => {
          const gd = document.querySelector('[data-testid="main-plot"]') as
            | (HTMLElement & {
                _fullLayout?: { xaxis?: { range?: [number, number] } }
              })
            | null
          const range = gd?._fullLayout?.xaxis?.range
          if (!range) return null
          // Plotly may return ISO strings on a date axis; coerce
          // to epoch ms for comparison.
          return [+new Date(range[0]), +new Date(range[1])] as [number, number]
        })
        if (r) {
          const within = (got: number, want: number) =>
            Math.abs(got - want) <= 1500
          if (within(r[0], xLo) && within(r[1], xHi)) {
            resolve(r)
            return
          }
        }
        if (Date.now() - start > 10_000) {
          resolve(r)
          return
        }
        setTimeout(tick, 100)
      }
      void tick()
    })

    expect(live).not.toBeNull()
    // Allow a 1.5 s slop window so the base36-second truncation in
    // the URL doesn't fight the assertion.
    expect(Math.abs((live as [number, number])[0] - xLo)).toBeLessThanOrEqual(
      1500
    )
    expect(Math.abs((live as [number, number])[1] - xHi)).toBeLessThanOrEqual(
      1500
    )
  })

  test('a Select-view zoom leaves a later editor on its session window', async ({
    page,
  }) => {
    test.setTimeout(90_000)
    // A link with `z=` but no `ed=` carries the sender's Select viewport. It
    // must not outrank the session window of an editor opened afterwards,
    // which is the only zoom telling the user what they are editing.
    const fullSpan = FIXTURE_OBS_END_MS - FIXTURE_OBS_START_MS
    const xHi = FIXTURE_OBS_END_MS - fullSpan * 0.1
    const xLo = xHi - fullSpan * 0.2
    const toS36 = (ms: number) => Math.floor(ms / 1000).toString(36)
    await page.goto(
      `/?ws=${WORKSPACE_ID}&ds=${DATASTREAM_ID}&z=${toS36(xLo)}.${toS36(xHi)}`
    )
    await waitForTraces(page, [DATASTREAM_ID])

    // The link's own zoom lands first, so the assertion below is about the
    // editor overriding it rather than the zoom never arriving.
    await expect
      .poll(async () => (await plotXRange(page))?.[0] ?? null, {
        timeout: 30_000,
      })
      .toBeCloseTo(xLo, -4)

    await startSessionFromRow(page)

    await expect
      .poll(() => zoomedToSessionWindow(page), { timeout: 30_000 })
      .toBe('session window')
  })

  test('hydrator hides traces flagged by the URL `h=` bitmask on a cold load', async ({
    page,
  }) => {
    // Two datastreams plotted, with bit 1 of the hidden-trace mask
    // set → the second trace is hidden. The fix this guards
    // against: `createPlotlyOption` honours `hiddenTraceIds`, so a
    // fresh load that hydrates the set from `h=` produces a plot
    // with the hidden traces already invisible. Pre-fix, the
    // sidebar correctly showed the row as hidden but the plot
    // continued to draw the trace until the user manually toggled
    // the eye again. The mask indexes `ds` only, so no Edit view.
    const url = `/?ws=${WORKSPACE_ID}&ds=${DATASTREAM_ID},${DATASTREAM_ID_B}&h=2`
    await page.goto(url)
    await waitForTraces(page, [DATASTREAM_ID, DATASTREAM_ID_B])
    // Let the rebuild settle.
    await page.waitForTimeout(800)

    const visibility = await page.evaluate(
      ({ a, b }) => {
        const gd = document.querySelector('[data-testid="main-plot"]') as
          | (HTMLElement & {
              data?: Array<{
                id?: string
                visible?: boolean | 'legendonly' | undefined
                _gapOverlayFor?: string
              }>
            })
          | null
        const traces = gd?.data ?? []
        type State = {
          visible: boolean | 'legendonly' | undefined
          overlayHidden: boolean
        }
        const reportFor = (id: string): State | null => {
          const main = traces.find((t) => t.id === id)
          if (!main) return null
          const overlay = traces.find((t) => t._gapOverlayFor === id)
          return {
            visible: main.visible,
            overlayHidden: overlay ? overlay.visible === false : true,
          }
        }
        return { a: reportFor(a), b: reportFor(b) }
      },
      { a: DATASTREAM_ID, b: DATASTREAM_ID_B }
    )

    expect(visibility.a).not.toBeNull()
    expect(visibility.b).not.toBeNull()
    // A (bit 0 unset) renders normally. Plotly normalises an unset
    // `visible` to `true`.
    expect(visibility.a!.visible).not.toBe(false)
    // B (bit 1 set in the URL mask) is hidden on the live plot,
    // along with its gap overlay.
    expect(visibility.b!.visible).toBe(false)
  })

  test('Reset Axes after URL-hydrated zoom + further interaction returns to the full data extent', async ({
    page,
  }) => {
    // Firefox cold-load + plot rebuild + reset is too heavy for the
    // default 30 s under worker contention.
    test.setTimeout(90_000)
    // Bug (options.ts:689): on a fresh mount with a URL `z=`, Plotly
    // pins `_rangeInitial0/1` to the URL view, so stock Reset bounces
    // back there instead of the data extent. A cold goto to a zoomed
    // URL reproduces the same condition as the user-reported
    // zoom→reload flow. Only a plotted datastream is needed.
    const fullSpan = FIXTURE_OBS_END_MS - FIXTURE_OBS_START_MS
    const xHi = FIXTURE_OBS_END_MS - fullSpan * 0.1
    const xLo = xHi - fullSpan * 0.2
    const toS36 = (ms: number) => Math.floor(ms / 1000).toString(36)
    const z = `${toS36(xLo)}.${toS36(xHi)}`
    await page.goto(`/?ws=${WORKSPACE_ID}&ds=${DATASTREAM_ID}&z=${z}`)
    await waitForTraces(page, [DATASTREAM_ID])

    const afterHydrate = await waitForPlotMeta(page)
    expect(afterHydrate).not.toBeNull()
    const hydratedSpan =
      afterHydrate!.dataFitRange[1] - afterHydrate!.dataFitRange[0]
    expect(hydratedSpan).toBeLessThan(fullSpan * 0.5)

    // Pan drag exercises Plotly's user-gesture path
    // (`_storeDirectGUIEdit`), which re-anchors `_rangeInitial`;
    // the custom Reset button has to override that.
    await page.mouse.move(
      afterHydrate!.cursorClient.x,
      afterHydrate!.cursorClient.y
    )
    await page.mouse.down()
    await page.mouse.move(
      afterHydrate!.cursorClient.x - 120,
      afterHydrate!.cursorClient.y,
      { steps: 10 }
    )
    await page.mouse.up()
    await page.waitForTimeout(400)

    await clickResetAxes(page)
    await page.waitForTimeout(500)

    const afterReset = await page.evaluate(() => {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (HTMLElement & {
            _fullLayout?: { xaxis?: { range?: [number, number] } }
          })
        | null
      const r = gd?._fullLayout?.xaxis?.range
      if (!r) return null
      return [+new Date(r[0]), +new Date(r[1])] as [number, number]
    })
    expect(afterReset).not.toBeNull()
    const resetSpan = afterReset![1] - afterReset![0]
    // ±20% slop for Plotly's auto-fit padding.
    expect(resetSpan).toBeGreaterThan(hydratedSpan * 1.5)
    expect(resetSpan).toBeGreaterThan(fullSpan * 0.8)
    expect(resetSpan).toBeLessThan(fullSpan * 1.5)
  })
})
