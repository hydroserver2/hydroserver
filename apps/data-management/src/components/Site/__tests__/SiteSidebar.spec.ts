import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import SitePhotoCarousel from '../SitePhotoCarousel.vue'
import SiteTagList from '../SiteTagList.vue'

const photo = (id: string, name: string) => ({
  id,
  name,
  type: 'Photo',
  link: `https://example.com/${id}.png`,
})

describe('SitePhotoCarousel', () => {
  it('renders nothing when the site has no photos', () => {
    const wrapper = mount(SitePhotoCarousel, {
      props: { photos: [] },
      global: { plugins: [vuetify] },
    })
    expect(wrapper.find('.site-photo-carousel').exists()).toBe(false)
  })

  it('steps through photos and wraps around', async () => {
    const wrapper = mount(SitePhotoCarousel, {
      props: { photos: [photo('a', 'Upstream'), photo('b', 'Downstream')] },
      global: { plugins: [vuetify] },
    })
    expect(wrapper.text()).toContain('Upstream')
    expect(wrapper.text()).toContain('1 of 2')

    await wrapper.get('[aria-label="Next photo"]').trigger('click')
    expect(wrapper.text()).toContain('Downstream')
    expect(wrapper.text()).toContain('2 of 2')

    await wrapper.get('[aria-label="Next photo"]').trigger('click')
    expect(wrapper.text()).toContain('1 of 2')

    await wrapper.get('[aria-label="Previous photo"]').trigger('click')
    expect(wrapper.text()).toContain('2 of 2')
  })

  it('asks the page to show every photo', async () => {
    const wrapper = mount(SitePhotoCarousel, {
      props: { photos: [photo('a', 'Upstream')] },
      global: { plugins: [vuetify] },
    })
    expect(wrapper.find('[aria-label="Next photo"]').exists()).toBe(false)
    await wrapper.get('[data-testid="site-photo-carousel-view-all"]').trigger('click')
    expect(wrapper.emitted('view-all')).toHaveLength(1)
  })
})

describe('SiteTagList', () => {
  it('shows each tag as a key with its value and links URLs', () => {
    const wrapper = mount(SiteTagList, {
      props: {
        tags: {
          watershed: 'Logan River',
          homepage: 'https://lro.usu.edu',
        },
      },
      global: { plugins: [vuetify] },
    })
    const watershed = wrapper.get('[data-testid="site-tag-watershed"]')
    expect(watershed.get('dt').text()).toBe('watershed')
    expect(watershed.get('dd').text()).toBe('Logan River')
    const link = wrapper.get('[data-testid="site-tag-homepage"] a')
    expect(link.attributes('href')).toBe('https://lro.usu.edu')
    expect(wrapper.find('[data-testid="edit-site-tags-button"]').exists()).toBe(false)
  })

  it('lists tags alphabetically by key, ignoring case', () => {
    const wrapper = mount(SiteTagList, {
      props: {
        tags: { watershed: 'a', HUC10: 'b', bank: 'c', HUC2: 'd', Access: 'e' },
      },
      global: { plugins: [vuetify] },
    })
    const keys = wrapper.findAll('dt').map((dt) => dt.text())
    expect(keys).toEqual(['Access', 'bank', 'HUC2', 'HUC10', 'watershed'])
  })

  it('hides the filter when there are only a few tags', () => {
    const wrapper = mount(SiteTagList, {
      props: { tags: { watershed: 'Logan River', network: 'LRO' } },
      global: { plugins: [vuetify] },
    })
    expect(wrapper.find('[data-testid="site-tag-filter"]').exists()).toBe(false)
  })

  it('filters long tag lists by key or value, ignoring case', async () => {
    const tags = {
      watershed: 'Logan River',
      network: 'Logan River Observatory',
      datalogger: 'Campbell Scientific CR1000X',
      telemetry: 'Cellular modem',
      power: 'Solar panel and battery',
      access: 'Park at the pull-out by the bridge',
      bank: 'East bank',
    }
    const wrapper = mount(SiteTagList, {
      props: { tags },
      global: { plugins: [vuetify] },
    })
    const input = wrapper.get('[data-testid="site-tag-filter"] input')

    await input.setValue('LOGAN')
    expect(wrapper.findAll('.site-tag-list__item')).toHaveLength(2)
    expect(wrapper.text()).toContain('2 of 7 tags')

    await input.setValue('power')
    const keys = wrapper.findAll('dt').map((dt) => dt.text())
    expect(keys).toEqual(['power'])

    await input.setValue('no such tag')
    expect(wrapper.findAll('.site-tag-list__item')).toHaveLength(0)
    expect(wrapper.text()).toContain('No tags match “no such tag”.')
  })

  it('shows an empty state and the edit button for editors', () => {
    const wrapper = mount(SiteTagList, {
      props: { tags: {}, canEdit: true },
      global: { plugins: [vuetify] },
    })
    expect(wrapper.text()).toContain('No tags yet.')
    expect(wrapper.find('[data-testid="edit-site-tags-button"]').exists()).toBe(true)
  })
})
