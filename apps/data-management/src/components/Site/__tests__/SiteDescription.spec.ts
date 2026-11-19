import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import SiteDescription from '../SiteDescription.vue'

// jsdom has no layout, so fake how tall the text is versus its 3.5-line cap.
function stubTextHeights(scrollHeight: number, clientHeight: number) {
  vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(
    scrollHeight
  )
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(
    clientHeight
  )
}

afterEach(() => vi.restoreAllMocks())

describe('SiteDescription', () => {
  it('shows short descriptions in full with no toggle', () => {
    stubTextHeights(40, 40)
    const wrapper = mount(SiteDescription, { global: { plugins: [vuetify] }, props: { text: 'A short note.' } })
    expect(wrapper.text()).toContain('A short note.')
    expect(wrapper.find('[data-testid="site-description-toggle"]').exists()).toBe(
      false
    )
  })

  it('collapses long descriptions behind "View more" and expands on click', async () => {
    stubTextHeights(200, 70)
    const wrapper = mount(SiteDescription, { global: { plugins: [vuetify] }, props: { text: 'Long text '.repeat(80) } })
    await nextTick() // overflow is measured on mount, then rendered
    const toggle = wrapper.get('[data-testid="site-description-toggle"]')
    expect(toggle.text()).toBe('View more')
    expect(toggle.attributes('aria-expanded')).toBe('false')

    await toggle.trigger('click')
    expect(wrapper.classes()).toContain('site-description--expanded')
    expect(toggle.text()).toBe('View less')
    expect(toggle.attributes('aria-expanded')).toBe('true')

    await toggle.trigger('click')
    expect(wrapper.classes()).not.toContain('site-description--expanded')
  })

  it('falls back to a placeholder when there is no description', () => {
    stubTextHeights(20, 20)
    const wrapper = mount(SiteDescription, { global: { plugins: [vuetify] }, props: { text: '' } })
    expect(wrapper.text()).toContain('No description provided.')
  })
})
