import '@hydroserver/design-system/components.css'

import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import { HsQuerySearchInput } from '@hydroserver/design-system/vue'
import { parseDatastreamQuery } from '@/utils/datastreamSearch'

describe('HsQuerySearchInput', () => {
  const qualifiers = [
    { key: 'site', label: 'Sites', values: ['Logan River', 'Bear River'] },
    { key: 'unit', label: 'Units', values: ['Feet'] },
  ]

  function mountSearch(modelValue = '') {
    const wrapper = mount(HsQuerySearchInput, {
      attachTo: document.body,
      props: {
        modelValue,
        placeholder: 'Search datastreams…',
        qualifiers,
        'onUpdate:modelValue': (value: string) =>
          wrapper.setProps({ modelValue: value }),
      },
      global: { stubs: { 'v-icon': true } },
    })
    return wrapper
  }

  it('keeps suggesting a site name across spaces and quotes the selected name', async () => {
    const wrapper = mountSearch()
    const input = wrapper.get('input')
    for (const value of ['site:L', 'site:Logan ', 'site:Logan R']) {
      await input.setValue(value)
      expect(
        document.querySelector('[role="option"]')?.textContent?.trim()
      ).toBe('Logan River')
    }
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.props('modelValue')).toBe('site:"Logan River" ')
    expect(
      parseDatastreamQuery(wrapper.props('modelValue')).filters.site
    ).toEqual(['Logan River'])
    wrapper.unmount()
  })

  it('recognizes a complete unquoted name without accepting a suggestion', async () => {
    const wrapper = mountSearch()
    await wrapper.get('input').setValue('site:Logan River')
    expect(wrapper.get('.hl-value-valid').text()).toBe('Logan River')
    expect(
      parseDatastreamQuery(wrapper.props('modelValue'), qualifiers).filters.site
    ).toEqual(['Logan River'])
    wrapper.unmount()
  })

  it('highlights only the hovered suggestion and selects it with Enter', async () => {
    const wrapper = mountSearch()
    const input = wrapper.get('input')
    await input.setValue('site:')
    const options = wrapper.findAll('[role="option"]')
    expect(options.map((option) => option.attributes('aria-selected'))).toEqual(
      ['true', 'false']
    )

    await options[1]!.trigger('mouseenter')
    expect(options.map((option) => option.attributes('aria-selected'))).toEqual(
      ['false', 'true']
    )
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.props('modelValue')).toBe('site:"Bear River" ')

    await input.setValue('site:')
    await wrapper.findAll('[role="option"]')[1]!.trigger('mouseenter')
    await wrapper.get('[role="listbox"]').trigger('mouseleave')
    expect(
      wrapper
        .findAll('[role="option"]')
        .map((option) => option.attributes('aria-selected'))
    ).toEqual(['true', 'false'])
    wrapper.unmount()
  })

  it('replaces the whole value when editing inside quotes and preserves later filters', async () => {
    const wrapper = mountSearch('site:"Logan River" unit:Feet')
    const input = wrapper.get('input')
    input.element.setSelectionRange(9, 9)
    await input.trigger('focus')
    await input.trigger('keydown', { key: 'Tab' })
    expect(wrapper.props('modelValue')).toBe('site:"Logan River" unit:Feet')
    wrapper.unmount()
  })

  it('keeps free text and later qualifier suggestions separate from a site name', async () => {
    const wrapper = mountSearch()
    const input = wrapper.get('input')
    await input.setValue('site:Logan River temperature un')
    expect(document.querySelector('[role="option"]')?.textContent?.trim()).toBe(
      'unit:'
    )
    wrapper.unmount()
  })

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

  it('clears the search query and filters from the trailing button', async () => {
    const wrapper = mount(HsQuerySearchInput, {
      props: {
        modelValue: 'status:Failed temperature',
        placeholder: 'Search tasks…',
        qualifiers: [{ key: 'status', label: 'Status', values: ['Failed'] }],
      },
      global: {
        stubs: {
          'v-icon': true,
        },
      },
    })

    await wrapper
      .get('button[aria-label="Clear search and filters"]')
      .trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([['']])
    expect(wrapper.emitted('clear')).toHaveLength(1)
  })
})
