// Module shim: route the bare specifier `plotly.js-dist` (the runtime bundle
// shipped without its own .d.ts) to the typed `plotly.js` namespace provided
// by @types/plotly.js. See CONV-013 — Plotly types are owned by this package
// and `src/utils/plotting/plotly.ts`.
declare module 'plotly.js-dist' {
  export * from 'plotly.js'
  export { default } from 'plotly.js'
}

// PRIVATE-API surface for the seam (`utils/plotting/plotly.ts`) only.
//
// `_fullLayout` and `xaxis/yaxis.p2c()` are undocumented Plotly internals
// used by `handleMouseMove` to convert mouse pixel positions into data
// coordinates. They are NOT covered by `@types/plotly.js`.
//
// Intentionally NOT a global augmentation of `Plotly.PlotlyHTMLElement` —
// keeping the private surface scoped to a separate exported interface so
// only the seam (which performs an explicit `as PrivatePlotlyHTMLElement`
// cast at the call site) can see it. Callers consuming the published
// `Plotly.PlotlyHTMLElement` shape continue to see the documented surface.
declare module 'plotly.js-dist' {
  export interface PrivatePlotlyAxis {
    p2c(pixel: number): number
  }

  export interface PrivatePlotlyFullLayout {
    xaxis: PrivatePlotlyAxis
    yaxis: PrivatePlotlyAxis
    margin: {
      l: number
      t: number
      r: number
      b: number
    }
  }

  export interface PrivatePlotlyHTMLElement extends import('plotly.js').PlotlyHTMLElement {
    _fullLayout: PrivatePlotlyFullLayout
  }
}
