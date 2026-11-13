import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { HsTableFilterMenu } from '@hydroserver/design-system/vue'

const options = [
  { value: 'alpha', label: 'Alpha' },
  { value: 'beta', label: 'Beta' },
  { value: 'gamma', label: 'Gamma' },
]
function mountMenu(selected: string[], extra = {}) {
  return mount(HsTableFilterMenu, {
    props: {
      title: 'Filter by unit',
      label: 'Unit',
      sectionLabel: 'Units',
      options,
      selected,
      ...extra,
    },
    global: {
      stubs: {
        'v-menu': { name: 'VMenu', template: '<div><slot /></div>' },
        'v-card': { template: '<div><slot /></div>' },
        'v-list': { template: '<div><slot /></div>' },
        'v-list-item': {
          template: '<div><slot name="prepend" /><slot /></div>',
        },
        'v-list-item-title': { template: '<div><slot /></div>' },
        'v-checkbox-btn': {
          props: ['modelValue'],
          template: '<input type="checkbox" :checked="modelValue" />',
        },
        'v-icon': true,
        'v-divider': true,
      },
    },
  })
}

describe('HsTableFilterMenu', () => {
  it('omits section banners without selections while keeping the title and search', () => {
    const wrapper = mountMenu([])
    expect(
      wrapper.findAll('.hs-table-filter-menu__section-title')
    ).toHaveLength(0)
    expect(wrapper.findAll('.hs-table-filter-menu__option')).toHaveLength(3)
    const header = wrapper.get('.hs-table-filter-menu__header')
    expect(header.text()).toContain('Filter by unit')
    expect(header.find('input').exists()).toBe(true)
    wrapper.unmount()
  })

  it('groups selections before other options without duplicates or a clear-all action', () => {
    const wrapper = mountMenu(['gamma', 'alpha'])
    expect(
      wrapper
        .findAll('.hs-table-filter-menu__selected input')
        .map((item) => item.attributes('aria-label'))
    ).toEqual(['Unit: Gamma', 'Unit: Alpha'])
    expect(wrapper.get('.hs-table-filter-menu__available').text()).toContain(
      'Beta'
    )
    expect(wrapper.findAll('.hs-table-filter-menu__option')).toHaveLength(3)
    expect(wrapper.text()).not.toContain('Clear filter')
    expect(
      wrapper.get('.hs-table-filter-menu__header').find('input').exists()
    ).toBe(true)
    expect(
      wrapper.get('.hs-table-filter-menu__options').find('header').exists()
    ).toBe(false)
    wrapper.unmount()
  })

  it('keeps selected values removable when search or another facet excludes them', async () => {
    const wrapper = mountMenu(['gamma', 'unavailable'], {
      caseInsensitive: true,
    })
    await wrapper.get('.hs-search__input').setValue('beta')
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).toContain(
      'Gamma'
    )
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).toContain(
      'unavailable'
    )
    expect(wrapper.get('.hs-table-filter-menu__available').text()).toContain(
      'Beta'
    )
    await wrapper.get('input[aria-label="Unit: unavailable"]').trigger('click')
    expect(wrapper.emitted('toggle')).toEqual([['unavailable']])
    wrapper.unmount()
  })

  it('matches query values case-insensitively and toggles only the clicked value', async () => {
    const wrapper = mountMenu(['GAMMA', 'alpha'], { caseInsensitive: true })
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).toContain(
      'Gamma'
    )
    expect(wrapper.get('.hs-table-filter-menu__available').text()).toContain(
      'Beta'
    )
    await wrapper.get('input[aria-label="Unit: Gamma"]').trigger('click')
    expect(wrapper.emitted('toggle')).toEqual([['GAMMA']])
    await wrapper.setProps({ selected: ['alpha'] })
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).toContain(
      'Gamma'
    )
    expect(
      (
        wrapper.get('input[aria-label="Unit: Gamma"]')
          .element as HTMLInputElement
      ).checked
    ).toBe(false)
    const menu = wrapper.getComponent({ name: 'VMenu' })
    menu.vm.$emit('update:modelValue', true)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).not.toContain(
      'Gamma'
    )
    expect(wrapper.get('.hs-table-filter-menu__available').text()).toContain(
      'Gamma'
    )
    wrapper.unmount()
  })

  it('keeps checked options in their opening sections until the menu is reopened', async () => {
    const wrapper = mountMenu(['alpha'])
    const menu = wrapper.getComponent({ name: 'VMenu' })
    menu.vm.$emit('update:modelValue', true)
    await wrapper.vm.$nextTick()
    await wrapper.setProps({
      selected: ['alpha', 'gamma'],
      options: [...options, { value: 'delta', label: 'Delta' }],
    })
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).toContain(
      'Alpha'
    )
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).not.toContain(
      'Gamma'
    )
    expect(wrapper.get('.hs-table-filter-menu__available').text()).toContain(
      'Gamma'
    )
    expect(wrapper.text()).not.toContain('Delta')
    expect(
      (
        wrapper.get('input[aria-label="Unit: Gamma"]')
          .element as HTMLInputElement
      ).checked
    ).toBe(true)
    menu.vm.$emit('update:modelValue', false)
    await wrapper.vm.$nextTick()
    menu.vm.$emit('update:modelValue', true)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.hs-table-filter-menu__selected').text()).toContain(
      'Gamma'
    )
    expect(
      wrapper.get('.hs-table-filter-menu__available').text()
    ).not.toContain('Gamma')
    expect(wrapper.get('.hs-table-filter-menu__available').text()).toContain(
      'Delta'
    )
    expect(
      wrapper
        .findAll('.hs-table-filter-menu__section-title')
        .map((banner) => banner.text())
    ).toEqual(['Selected units', 'Units'])
    wrapper.unmount()
  })

  it('exposes checked states for compact menus and allows row toggles', async () => {
    const wrapper = mountMenu(['gamma'], {
      searchable: false,
      showCheckboxes: false,
    })
    expect(wrapper.find('input').exists()).toBe(false)
    const selected = wrapper.get(
      '[role="menuitemcheckbox"][aria-checked="true"]'
    )
    expect(selected.text()).toBe('Gamma')
    await selected.trigger('click')
    expect(wrapper.emitted('toggle')).toEqual([['gamma']])
    wrapper.unmount()
  })
})
