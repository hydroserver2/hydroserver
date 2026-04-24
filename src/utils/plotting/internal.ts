import type { PlotlyHTMLElement } from 'plotly.js-dist'

// DATA-CAST: Plotly.Data.x is typed broadly (Datum[] | Datum[][] | TypedArray
// | undefined) but every trace this app produces stores numeric epoch
// timestamps in `x`. Centralise the cast here so binary-search call sites
// (findFirstGreaterOrEqual in handleRelayout / fitYaxisToVisible) get number[]
// without scattering `as number[]` across the file. If we ever introduce
// non-numeric x data, this is the single place to reconsider.
export const traceXAsNumbers = (
  gd: PlotlyHTMLElement | null | undefined,
  traceIndex: number
): number[] => {
  const x = gd?.data[traceIndex]?.x
  return (x ?? []) as number[]
}

// Marker-density threshold. Above this many visible points per trace,
// scattergl markers are rendered at `opacity: 0` (still hit-testable for
// select/lasso, just invisible) so the plot doesn't turn into ink soup.
export const DENSITY_HIDE_MARKERS = 2000

export const Y_AXIS_KEY_RE = /^yaxis\d*$/
