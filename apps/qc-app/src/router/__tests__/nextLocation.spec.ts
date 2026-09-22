import { describe, it, expect } from 'vitest'
import { nextLocation } from '@/router/nextLocation'

describe('nextLocation', () => {
  it('treats a plain value as a route name', () => {
    expect(nextLocation('Home')).toEqual({ name: 'Home' })
  })

  it('treats a leading slash as a path', () => {
    expect(nextLocation('/some/page')).toEqual({ path: '/some/page' })
  })

  it('falls back to Home', () => {
    expect(nextLocation(undefined)).toEqual({ name: 'Home' })
    expect(nextLocation('')).toEqual({ name: 'Home' })
    expect(nextLocation(['Home'])).toEqual({ name: 'Home' })
  })
})
