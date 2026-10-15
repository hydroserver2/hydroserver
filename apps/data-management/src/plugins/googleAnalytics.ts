declare global {
  interface Window {
    dataLayer?: IArguments[]
    gtag?: (...args: unknown[]) => void
  }
}

export function injectGoogleAnalytics(measurementId: string) {
  const dataLayer = (window.dataLayer = window.dataLayer || [])
  window.gtag = function (..._args: unknown[]) {
    dataLayer.push(arguments)
  }
  window.gtag('js', new Date())
  // GA4 enhanced measurement tracks subsequent browser history changes.
  window.gtag('config', measurementId)

  const script = document.createElement('script')
  script.async = true
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`
  document.head.appendChild(script)
}
