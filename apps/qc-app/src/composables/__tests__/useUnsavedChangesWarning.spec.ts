import { describe, it, expect, beforeEach, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useUnsavedChangesWarning } from '../useUnsavedChangesWarning'

const dirty = ref(false)

const Host = defineComponent({
  setup() {
    useUnsavedChangesWarning(dirty)
    return () => null
  },
})

/** A beforeunload event that records whether the page tried to block it. */
const unloadEvent = () => {
  const event = new Event('beforeunload', { cancelable: true })
  Object.defineProperty(event, 'returnValue', { value: '', writable: true })
  return event
}

beforeEach(() => {
  dirty.value = false
})

describe('useUnsavedChangesWarning', () => {
  it('blocks the unload while there are unsaved changes', () => {
    const wrapper = mount(Host)
    dirty.value = true

    const event = unloadEvent()
    window.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(event.returnValue).toBe('')
    wrapper.unmount()
  })

  it('lets the unload through when everything is saved', () => {
    const wrapper = mount(Host)

    const event = unloadEvent()
    window.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(false)
    wrapper.unmount()
  })

  it('stops listening once the component is gone', () => {
    const wrapper = mount(Host)
    const remove = vi.spyOn(window, 'removeEventListener')
    wrapper.unmount()
    expect(remove).toHaveBeenCalledWith('beforeunload', expect.any(Function))

    dirty.value = true
    const event = unloadEvent()
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })
})
