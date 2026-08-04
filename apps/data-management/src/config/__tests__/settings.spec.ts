import { afterEach, describe, expect, it, vi } from 'vitest'

describe('development settings', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.resetModules()
  })

  it('uses defaults when the development API is unavailable', async () => {
    class FailingXMLHttpRequest {
      open() {}

      send() {
        throw new DOMException('Connection refused', 'NetworkError')
      }
    }

    vi.stubGlobal('XMLHttpRequest', FailingXMLHttpRequest)
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    vi.resetModules()

    const { settings } = await import('@/config/settings')

    expect(settings.mapConfiguration.defaultZoomLevel).toBe(2)
    expect(settings.authenticationConfiguration.providers).toEqual([])
    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('using defaults'),
      expect.any(DOMException)
    )
  })
})
