import { describe, it, expect, beforeEach } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { useUiLayoutStore } from '@/store/uiLayout'

beforeEach(() => {
  createTestPinia()
})

describe('useUiLayoutStore', () => {
  it('getSize returns null before any value is set', () => {
    const store = useUiLayoutStore()
    expect(store.getSize('sidebar')).toBeNull()
  })

  it('setSize then getSize round-trips a numeric value', () => {
    const store = useUiLayoutStore()
    store.setSize('sidebar', 320)
    expect(store.getSize('sidebar')).toBe(320)
  })

  it('setSize overwrites previous value for the same key', () => {
    const store = useUiLayoutStore()
    store.setSize('panel', 100)
    store.setSize('panel', 200)
    expect(store.getSize('panel')).toBe(200)
  })

  it('getFlag returns null before any value is set', () => {
    const store = useUiLayoutStore()
    expect(store.getFlag('collapsed')).toBeNull()
  })

  it('setFlag true/false round-trips through getFlag', () => {
    const store = useUiLayoutStore()
    store.setFlag('collapsed', true)
    expect(store.getFlag('collapsed')).toBe(true)
    store.setFlag('collapsed', false)
    expect(store.getFlag('collapsed')).toBe(false)
  })

  it('multiple size keys do not interfere', () => {
    const store = useUiLayoutStore()
    store.setSize('a', 10)
    store.setSize('b', 20)
    expect(store.getSize('a')).toBe(10)
    expect(store.getSize('b')).toBe(20)
  })

  it('multiple flag keys do not interfere', () => {
    const store = useUiLayoutStore()
    store.setFlag('a', true)
    store.setFlag('b', false)
    expect(store.getFlag('a')).toBe(true)
    expect(store.getFlag('b')).toBe(false)
  })

  it('size and flag maps are independent', () => {
    const store = useUiLayoutStore()
    store.setSize('shared', 50)
    store.setFlag('shared', true)
    expect(store.getSize('shared')).toBe(50)
    expect(store.getFlag('shared')).toBe(true)
  })
})
