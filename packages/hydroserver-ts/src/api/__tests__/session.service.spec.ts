import { describe, expect, it } from 'vitest'
import { HydroServer } from '../HydroServer'

describe('SessionService account URLs', () => {
  it('includes the app developer’s return destination', () => {
    const originalLocation = Object.getOwnPropertyDescriptor(globalThis, 'location')
    Object.defineProperty(globalThis, 'location', {
      configurable: true,
      value: { origin: 'https://app.example.test' },
    })

    const client = new HydroServer({ host: 'https://api.example.test' })

    try {
      expect(client.session.getAccountSignupUrl('/projects')).toBe(
        'https://api.example.test/accounts/signup/?next=https%3A%2F%2Fapp.example.test%2Fprojects'
      )
      expect(client.session.getAccountProfileUrl('/settings')).toBe(
        'https://api.example.test/accounts/profile/?next=https%3A%2F%2Fapp.example.test%2Fsettings'
      )
    } finally {
      if (originalLocation) {
        Object.defineProperty(globalThis, 'location', originalLocation)
      } else {
        Reflect.deleteProperty(globalThis, 'location')
      }
    }
  })

  it('uses the current app URL when a destination is not supplied', () => {
    const originalLocation = Object.getOwnPropertyDescriptor(globalThis, 'location')
    const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window')
    const location = {
      origin: 'http://localhost:1203',
      pathname: '/workspaces',
      search: '?tab=metadata',
      hash: '#details',
    }
    Object.defineProperty(globalThis, 'location', {
      configurable: true,
      value: location,
    })
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: { location },
    })

    const client = new HydroServer({ host: 'http://127.0.0.1:8000' })

    try {
      expect(client.session.getAccountProfileUrl()).toBe(
        'http://127.0.0.1:8000/accounts/profile/?next=http%3A%2F%2Flocalhost%3A1203%2Fworkspaces%3Ftab%3Dmetadata%23details'
      )
    } finally {
      if (originalLocation) {
        Object.defineProperty(globalThis, 'location', originalLocation)
      } else {
        Reflect.deleteProperty(globalThis, 'location')
      }
      if (originalWindow) {
        Object.defineProperty(globalThis, 'window', originalWindow)
      } else {
        Reflect.deleteProperty(globalThis, 'window')
      }
    }
  })
})
