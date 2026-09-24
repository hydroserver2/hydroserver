import { afterEach, describe, expect, it } from 'vitest'
import { injectGoogleAnalytics } from '../googleAnalytics'

afterEach(() => {
  document.head.innerHTML = ''
  delete window.dataLayer
  delete window.gtag
})

describe('Google Analytics', () => {
  it('loads the Google tag asynchronously and queues GA4 initialization', () => {
    injectGoogleAnalytics('G-TEST123456')

    const script = document.head.querySelector('script')!
    expect(script.async).toBe(true)
    expect(script.src).toBe(
      'https://www.googletagmanager.com/gtag/js?id=G-TEST123456'
    )
    expect(window.dataLayer?.map((entry) => Array.from(entry))).toEqual([
      ['js', expect.any(Date)],
      ['config', 'G-TEST123456'],
    ])
  })

  it('preserves an existing data layer and safely encodes the measurement ID', () => {
    const dataLayer: IArguments[] = []
    window.dataLayer = dataLayer
    const measurementId = 'G-TEST&extra="value"'

    injectGoogleAnalytics(measurementId)

    expect(window.dataLayer).toBe(dataLayer)
    const script = document.head.querySelector('script')!
    const url = new URL(script.src)
    expect(Array.from(url.searchParams)).toEqual([['id', measurementId]])
    expect(document.head.querySelectorAll('script')).toHaveLength(1)
    expect(Array.from(dataLayer[1])).toEqual(['config', measurementId])
  })
})
