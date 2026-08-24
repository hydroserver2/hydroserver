import '@hydroserver/design-tokens/components.css'

import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import HsQuerySearchInput from '@/components/base/HsQuerySearchInput.vue'

describe('HsQuerySearchInput', () => {
  afterEach(() => {
    document.body.replaceChildren()
    document.body.style.removeProperty('font-weight')
    document.documentElement.style.removeProperty('--hs-font-weight-semibold')
  })

  it('keeps highlighted qualifier values at the overlay font weight', () => {
    document.body.style.fontWeight = '400'
    document.documentElement.style.setProperty(
      '--hs-font-weight-semibold',
      '600'
    )

    const wrapper = mount(HsQuerySearchInput, {
      attachTo: document.body,
      props: {
        modelValue: 'type:Aggregation',
        placeholder: 'Search tasks…',
        qualifiers: [
          { key: 'type', label: 'Task type', values: ['Aggregation'] },
        ],
      },
      global: {
        stubs: {
          'v-icon': true,
        },
      },
    })

    const overlay = wrapper.get('.hs-query-search__highlight').element
    const highlightedValue = wrapper.get('.hl-value-valid').element
    const overlayWeight = getComputedStyle(overlay).fontWeight

    expect(overlayWeight).toBe('400')
    expect(getComputedStyle(highlightedValue).fontWeight).toBe(overlayWeight)
  })
})
