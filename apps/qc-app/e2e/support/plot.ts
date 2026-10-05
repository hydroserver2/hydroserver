/**
 * Reading the main plot's x values back as instants. In the browser's own
 * zone, which every spec here uses unless it picks another, the app hands
 * Plotly the instants themselves (see `src/utils/plotting/plotTime.ts`),
 * and a range string, which is that zone's clock, parses as browser-local
 * time.
 */

import type { Page } from '@playwright/test'

type PlotRoot = HTMLElement & {
  data?: Array<{ id?: string; x?: ArrayLike<number> }>
  _fullLayout?: { xaxis?: { range?: Array<number | string> } }
}

/** The main plot's live x range as `[loMs, hiMs]`, or null before it draws. */
export function plotXRange(page: Page): Promise<[number, number] | null> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    const r = gd?._fullLayout?.xaxis?.range
    if (!r || r.length !== 2) return null
    const toMs = (v: number | string) =>
      typeof v === 'number' ? v : Date.parse(v.replace(' ', 'T'))
    return [toMs(r[0]!), toMs(r[1]!)] as [number, number]
  })
}

/** Ids of the main plot's traces, in draw order. */
export function traceIds(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    return (gd?.data ?? []).map((t) => t.id ?? '').filter(Boolean)
  })
}

/** First and last x of a trace as instants, or null when it has none. */
export function traceXExtent(page: Page, id: string): Promise<[number, number] | null> {
  return page.evaluate((traceId) => {
    const gd = document.querySelector('[data-testid="main-plot"]') as PlotRoot
    const xs = (gd?.data ?? []).find((t) => t.id === traceId)?.x
    if (!xs?.length) return null
    return [xs[0]!, xs[xs.length - 1]!] as [number, number]
  }, id)
}
