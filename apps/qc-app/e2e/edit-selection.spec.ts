/**
 * Picking what to edit: the row Edit button, the window step, and what the
 * editor draws around the session.
 *   - Edit on a row does not plot it
 *   - the window step prefills a valid window and blocks an invalid one
 *   - the window step offers presets and a one-click fix
 *   - the editor draws the edit target, its source, and plotted datastreams
 *   - closing the editor keeps the plotted datastreams
 *   - the source is drawn only around the session window, with no shape
 *   - box select works over the session window, and Clear drops it
 *   - the stage band survives a redraw
 *   - the editor opens zoomed to the session window
 *   - changing the Context range keeps the user zoom
 *   - Context presets count out from the session window
 */

import { expect, test, type Locator, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import {
  gotoHome,
  openEditor,
  openOp,
  plotDatastreamById,
  setupEditView,
  startSessionFromRow,
  waitForEditorReady,
} from './support/app'
import {
  DATASTREAM_ID,
  DATASTREAM_ID_B,
  FIXTURE_OBS_END_MS,
  FIXTURE_OBS_START_MS,
  MANAGED_DATASTREAM_ID,
} from './support/fixtures'

type PlotRoot = HTMLElement & {
  data?: Array<{ id?: string; x?: Array<number | string> }>
  layout?: {
    shapes?: Array<{ name?: string }>
    xaxis?: { range?: Array<number | string> }
  }
}

function shapeNames(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    return (gd?.layout?.shapes ?? []).map((s) => s.name ?? '')
  })
}

// `COLORS[0]` and `SOURCE_CONTEXT_COLOR` in `src/utils/plotting/options.ts`.
const QC_COLOR = '#3f3f3f'
const SOURCE_COLOR = '#cfcfcf'

type DrawnTrace = {
  id?: string
  _partOf?: string
  x?: ArrayLike<number | string>
  line?: { color?: string }
  marker?: { color?: string }
  _isGapOverlay?: boolean
}

/** Every trace drawn for datastream `id`: its colour and x extent. */
function tracesOf(page: Page, id: string) {
  return page.evaluate((id) => {
    const gd = document.querySelector('[data-testid="main-plot"]') as
      | (HTMLElement & { data?: DrawnTrace[] })
      | null
    const ms = (v: number | string) =>
      typeof v === 'number' ? v : Date.parse(v)
    return (gd?.data ?? [])
      .filter((t) => t.id === id || t._partOf === id)
      .map((t) => {
        const xs = Array.from(t.x ?? [], ms).filter(Number.isFinite)
        return {
          line: !!t._isGapOverlay,
          color: t._isGapOverlay ? t.line?.color : t.marker?.color,
          count: xs.length,
          max: xs.length ? Math.max(...xs) : null,
        }
      })
  }, id)
}

type ReloadProbe = { __contextStart: number; __afterplots: number[] }

function traceIds(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    return (gd?.data ?? []).map((t) => t.id ?? '').filter(Boolean)
  })
}

/** Live x-axis range in epoch ms. Plotly date strings are UTC. */
function xRange(page: Page): Promise<[number, number] | null> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    const range = gd?.layout?.xaxis?.range
    if (!range || range.length !== 2) return null
    const toMs = (v: number | string) =>
      typeof v === 'number' ? v : Date.parse(`${v.replace(' ', 'T')}Z`)
    return [toMs(range[0]!), toMs(range[1]!)] as [number, number]
  })
}

/**
 * Type a local date and time into a `DatePickerField`. Its inputs mask
 * digit by digit, so select the whole value and type digits only.
 */
async function typeDateTime(field: Locator, when: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  const date = `${pad(when.getMonth() + 1)}${pad(when.getDate())}${when.getFullYear()}`
  const time = `${pad(when.getHours())}${pad(when.getMinutes())}`
  const inputs = field.locator('input')
  for (const [input, digits] of [
    [inputs.nth(0), date],
    [inputs.nth(1), time],
  ] as const) {
    await input.click()
    await input.evaluate((el: HTMLInputElement) =>
      el.setSelectionRange(0, el.value.length)
    )
    await input.pressSequentially(digits)
    await input.blur()
  }
}

/** First and last x of a trace in epoch ms. Plotly date strings are UTC. */
function traceXExtent(page: Page, id: string): Promise<[number, number] | null> {
  return page.evaluate((traceId) => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    const xs = (gd?.data ?? []).find((t) => t.id === traceId)?.x
    if (!xs?.length) return null
    const toMs = (v: number | string) =>
      typeof v === 'number' ? v : Date.parse(`${v.replace(' ', 'T')}Z`)
    return [toMs(xs[0]!), toMs(xs[xs.length - 1]!)] as [number, number]
  }, id)
}

/** What a `DatePickerField` shows for `when`: local MM/DD/YYYY and HH:MM. */
function pickerText(when: Date): [string, string] {
  const pad = (n: number) => String(n).padStart(2, '0')
  return [
    `${pad(when.getMonth() + 1)}/${pad(when.getDate())}/${when.getFullYear()}`,
    `${pad(when.getHours())}:${pad(when.getMinutes())}`,
  ]
}

async function openWindowStep(page: Page) {
  await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
  await page.getByTestId(`edit-managed-${MANAGED_DATASTREAM_ID}`).click()
  await expect(page.getByTestId('session-window-start')).toBeVisible()
}

test.describe('edit selection', () => {
  test.beforeEach(async ({ page }) => {
    test.slow()
    await installMocks(page, { qcHistories: true })
  })

  test('Edit on a row does not plot it', async ({ page }) => {
    await gotoHome(page)
    await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
    await expect(
      page.getByTestId(`edit-managed-${MANAGED_DATASTREAM_ID}`)
    ).toBeVisible()
    await page.getByTestId('chooser-cancel').click()
    await expect(
      page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`)
    ).toHaveAttribute('aria-pressed', 'false')
  })

  test('the window step prefills a valid window and blocks an invalid one', async ({
    page,
  }) => {
    await gotoHome(page)
    await openWindowStep(page)
    await expect(page.getByTestId('session-window-start')).toBeEnabled()
    await expect(page.getByTestId('session-window-error')).toBeHidden()
    await expect(page.getByTestId('session-window-committed')).not.toContainText(
      'Nothing committed'
    )

    // A From after the source ends is outside the source data.
    await typeDateTime(
      page.getByTestId('session-window-from'),
      new Date(FIXTURE_OBS_END_MS + 2 * 24 * 60 * 60 * 1000)
    )
    await expect(page.getByTestId('session-window-error')).toBeVisible()
    await expect(page.getByTestId('session-window-start')).toBeDisabled()
  })

  test('the window step offers presets and a one-click fix', async ({ page }) => {
    await gotoHome(page)
    await openWindowStep(page)

    // The fixture record spans about a day, fully committed: only All fits.
    await expect(page.getByTestId('session-window-preset-all')).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    await expect(page.getByTestId('session-window-preset-1m')).toHaveClass(
      /v-chip--disabled/
    )
    await expect(
      page.getByTestId('session-window-preset-slot-1m')
    ).toHaveAttribute('title', 'Longer than the record')

    const start = new Date(FIXTURE_OBS_START_MS)
    const end = new Date(FIXTURE_OBS_END_MS)
    await typeDateTime(
      page.getByTestId('session-window-from'),
      new Date(FIXTURE_OBS_START_MS - 2 * 24 * 60 * 60 * 1000)
    )
    await expect(page.getByTestId('session-window-start')).toBeDisabled()
    const fix = page.getByTestId('session-window-fix')
    await expect(fix).toContainText('Start at')
    await fix.click()

    await expect(page.getByTestId('session-window-error')).toBeHidden()
    await expect(page.getByTestId('session-window-start')).toBeEnabled()
    const [fromDate, fromTime] = pickerText(start)
    const [toDate, toTime] = pickerText(end)
    const from = page.getByTestId('session-window-from').locator('input')
    const to = page.getByTestId('session-window-to').locator('input')
    await expect(from.nth(0)).toHaveValue(fromDate)
    await expect(from.nth(1)).toHaveValue(fromTime)
    await expect(to.nth(0)).toHaveValue(toDate)
    await expect(to.nth(1)).toHaveValue(toTime)
  })

  test('the editor draws the source and plotted datastreams around the session', async ({
    page,
  }) => {
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await startSessionFromRow(page)

    await expect
      .poll(() => traceIds(page))
      .toEqual(
        expect.arrayContaining([
          MANAGED_DATASTREAM_ID,
          `ctx:${DATASTREAM_ID}`,
          DATASTREAM_ID_B,
        ])
      )

    await page.getByTestId('time-range-btn').click()
    await page
      .getByTestId('time-range-menu')
      .getByTestId('date-preset-All')
      .click()
    await expect(page.getByTestId('exit-save-btn')).toBeVisible()
  })

  test('closing the editor keeps the plotted datastreams', async ({ page }) => {
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await startSessionFromRow(page)
    await page.getByTestId('exit-close-btn').click()
    // The session was never touched, so closing asks what to do with it.
    await page.getByTestId('leave-keep-btn').click()
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
    await expect(
      page.getByTestId(`plot-checkbox-${DATASTREAM_ID_B}`)
    ).toHaveAttribute('aria-pressed', 'true')
    await expect(
      page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`)
    ).toHaveAttribute('aria-pressed', 'false')
  })

  test('the source is drawn only around the session window, with no shape', async ({
    page,
  }) => {
    await gotoHome(page)
    // Start the session halfway through the source, so the source has
    // context before it and nothing after.
    const mid = new Date((FIXTURE_OBS_START_MS + FIXTURE_OBS_END_MS) / 2)
    mid.setSeconds(0, 0)
    await openWindowStep(page)
    await typeDateTime(page.getByTestId('session-window-from'), mid)
    await page.getByTestId('session-window-start').click()
    await openEditor(page)

    await expect
      .poll(async () => (await tracesOf(page, `ctx:${DATASTREAM_ID}`)).length)
      .toBeGreaterThan(0)
    const source = await tracesOf(page, `ctx:${DATASTREAM_ID}`)
    expect(source.every((t) => t.color === SOURCE_COLOR)).toBe(true)
    expect(source.some((t) => t.count > 0)).toBe(true)
    // Points only: the bridge line reaches the edit target's first point.
    expect(
      source
        .filter((t) => !t.line)
        .every((t) => t.max === null || t.max < mid.getTime())
    ).toBe(true)

    const edit = await tracesOf(page, MANAGED_DATASTREAM_ID)
    expect(edit.every((t) => t.color === QC_COLOR)).toBe(true)
    expect(await shapeNames(page)).toEqual([])
  })

  test('box select works over the session window, and Clear drops it', async ({
    page,
  }) => {
    await setupEditView(page)
    await page.locator('.modebar-btn[data-title="Box Select"]').first().click()
    const box = (await page
      .locator('[data-testid="main-plot"] .nsewdrag')
      .first()
      .boundingBox())!
    await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.05)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.95, {
      steps: 10,
    })
    await page.mouse.up()

    const clear = page.getByTestId('clear-selection-btn')
    await expect(clear).toBeVisible()
    await clear.click()
    await expect(clear).toHaveCount(0)
  })

  test('the stage band survives a redraw', async ({ page }) => {
    await setupEditView(page)

    await openOp(page, 'gaps')
    await page.getByTestId('filter-range-enable-btn').click()
    await expect.poll(() => shapeNames(page)).toContain('stage')

    // A context reload redraws the plot; the stage band must survive it.
    await page.evaluate(() => {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (PlotRoot & { on: (event: string, cb: () => void) => void })
      const w = window as unknown as { __updates: number }
      w.__updates = 0
      gd.on('plotly_update', () => w.__updates++)
    })
    await page.getByTestId('time-range-btn').click()
    const menu = page.getByTestId('time-range-menu')
    const allActive = /v-chip--variant-tonal/.test(
      (await menu.getByTestId('date-preset-All').getAttribute('class')) ?? ''
    )
    await menu.getByTestId(allActive ? 'date-preset-1w' : 'date-preset-All').click()
    await page.waitForFunction(
      () => (window as unknown as { __updates: number }).__updates > 0
    )
    await page.keyboard.press('Escape')
    expect(await shapeNames(page)).toEqual(['stage'])

    await page.getByTestId('filter-range-disable-btn').click()
    await expect.poll(() => shapeNames(page)).toEqual([])
  })

  test('the editor opens zoomed to the session window', async ({ page }) => {
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await page.getByTestId('time-range-btn').click()
    await page.getByTestId('time-range-menu').getByTestId('date-preset-All').click()
    await page.keyboard.press('Escape')

    // Start the session halfway through the source, so the window is
    // narrower than the context around it.
    const mid = new Date((FIXTURE_OBS_START_MS + FIXTURE_OBS_END_MS) / 2)
    mid.setSeconds(0, 0)
    await openWindowStep(page)
    await typeDateTime(page.getByTestId('session-window-from'), mid)
    await expect(page.getByTestId('session-window-start')).toBeEnabled()
    await page.getByTestId('session-window-start').click()
    await openEditor(page)

    const tolerance = 60_000
    await expect
      .poll(async () => {
        const r = await xRange(page)
        return (
          !!r &&
          Math.abs(r[0] - mid.getTime()) <= tolerance &&
          Math.abs(r[1] - FIXTURE_OBS_END_MS) <= tolerance
        )
      })
      .toBe(true)
  })

  test('changing the Context range keeps the user zoom', async ({ page }) => {
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await page.getByTestId('time-range-btn').click()
    await page.getByTestId('time-range-menu').getByTestId('date-preset-All').click()
    await page.keyboard.press('Escape')
    await startSessionFromRow(page)
    await expect.poll(() => xRange(page)).not.toBeNull()
    const opened = (await xRange(page))!

    // Zoom in with the wheel so the view differs from the session window.
    const box = (await page.getByTestId('main-plot').boundingBox())!
    await page.mouse.move(box.x + box.width * 0.4, box.y + box.height / 2)
    for (let i = 0; i < 4; i++) await page.mouse.wheel(0, -200)
    await expect
      .poll(async () => {
        const r = await xRange(page)
        return !!r && r[1] - r[0] < (opened[1] - opened[0]) * 0.9
      })
      .toBe(true)
    const zoomed = (await xRange(page))!

    await page.getByTestId('time-range-btn').click()
    const menu = page.getByTestId('time-range-menu')

    // Record every redraw from here on, in page time, so none is missed.
    await page.evaluate(() => {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (PlotRoot & { on: (event: string, cb: () => void) => void })
      const w = window as unknown as ReloadProbe
      // Dev-server module loads fill the default resource timing buffer.
      performance.clearResourceTimings()
      performance.setResourceTimingBufferSize(1_000)
      w.__contextStart = performance.now()
      w.__afterplots = []
      gd.on('plotly_afterplot', () => w.__afterplots.push(performance.now()))
    })
    // 1w, not All: All is already the context, so picking it changes nothing.
    await menu.getByTestId('date-preset-1w').click()
    await expect(menu.getByTestId('date-preset-1w')).toHaveClass(
      /v-chip--variant-tonal/
    )
    await expect(menu.getByTestId('date-preset-All')).not.toHaveClass(
      /v-chip--variant-tonal/
    )
    // The reload redraws the context. All was loaded already, so the cache
    // answers it without a request, and the edit target is never refetched.
    await page.waitForFunction(
      () => (window as unknown as ReloadProbe).__afterplots.length > 0
    )
    await expect(page.getByTestId('data-loading-indicator')).toHaveCount(0)
    const editFetched = await page.evaluate((id) => {
      const w = window as unknown as ReloadProbe
      return performance
        .getEntriesByType('resource')
        .some(
          (e) =>
            e.startTime >= w.__contextStart &&
            e.name.includes(`/datastreams/${id}/observations`)
        )
    }, MANAGED_DATASTREAM_ID)
    expect(editFetched).toBe(false)
    expect(await traceIds(page)).toContain(MANAGED_DATASTREAM_ID)

    // Sample the range over several frames so a late redraw would show up.
    const drift = await page.evaluate(async ([lo, hi]) => {
      const toMs = (v: number | string) =>
        typeof v === 'number' ? v : Date.parse(`${v.replace(' ', 'T')}Z`)
      let worst = 0
      const end = performance.now() + 1_500
      while (performance.now() < end) {
        const gd = document.querySelector('[data-testid="main-plot"]') as
          | (HTMLElement & { layout?: { xaxis?: { range?: Array<number | string> } } })
          | null
        const r = gd?.layout?.xaxis?.range
        if (!r) return Infinity
        worst = Math.max(
          worst,
          Math.abs(toMs(r[0]!) - lo!),
          Math.abs(toMs(r[1]!) - hi!)
        )
        await new Promise((res) => setTimeout(res, 100))
      }
      return worst
    }, zoomed)
    expect(drift).toBeLessThanOrEqual(1_000)
    expect(await traceIds(page)).toContain(MANAGED_DATASTREAM_ID)
  })

  test('Context presets count out from the session window', async ({ page }) => {
    await gotoHome(page)
    // Start halfway through the source, so the window has data before it.
    const mid = new Date((FIXTURE_OBS_START_MS + FIXTURE_OBS_END_MS) / 2)
    mid.setSeconds(0, 0)
    await openWindowStep(page)
    await typeDateTime(page.getByTestId('session-window-from'), mid)
    await expect(page.getByTestId('session-window-start')).toBeEnabled()
    await page.getByTestId('session-window-start').click()
    await openEditor(page)

    await page.getByTestId('time-range-btn').click()
    const menu = page.getByTestId('time-range-menu')
    await expect(menu.getByTestId('date-preset-YTD')).toHaveCount(0)
    await menu.getByTestId('date-preset-1w').click()
    await expect(menu.getByTestId('date-preset-1w')).toHaveClass(
      /v-chip--variant-tonal/
    )
    await expect(page.getByTestId('data-loading-indicator')).toHaveCount(0)

    // The fixture spans about 30 hours, so any 1w range loads all of it and
    // the trace alone cannot tell the rules apart. The loaded range can:
    // counting back from the data end would put To at the data end.
    const expectedFrom = new Date(mid)
    expectedFrom.setDate(expectedFrom.getDate() - 7)
    const expectedTo = new Date(FIXTURE_OBS_END_MS)
    expectedTo.setDate(expectedTo.getDate() + 7)
    const fieldText = (id: string) =>
      menu.getByTestId(id).locator('input').evaluateAll((inputs) =>
        inputs.map((i) => (i as HTMLInputElement).value)
      )
    await expect.poll(() => fieldText('date-range-from')).toEqual(pickerText(expectedFrom))
    await expect.poll(() => fieldText('date-range-to')).toEqual(pickerText(expectedTo))

    // The grey source runs from the data start (the week before the window,
    // clamped to the fixture) and stops at the window.
    const tolerance = 60_000
    await expect
      .poll(async () => {
        const x = await traceXExtent(page, `ctx:${DATASTREAM_ID}`)
        return (
          !!x &&
          Math.abs(x[0] - FIXTURE_OBS_START_MS) <= tolerance &&
          x[1] < mid.getTime()
        )
      })
      .toBe(true)
  })
})
