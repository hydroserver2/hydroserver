import { shallowMount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { mdiDotsVertical } from '@mdi/js'
import DatastreamSiteButton from '../DatastreamSiteButton.vue'

describe('DatastreamSiteButton', () => {
  it('shows site and visualization deep links in menu mode', () => {
    const wrapper = shallowMount(DatastreamSiteButton, {
      props: {
        datastreamId: 'datastream-1',
        fallbackMonitoringSiteId: 'site-1',
        showMenu: true,
      },
      global: {
        stubs: {
          VBtnIcon: {
            name: 'VBtnIcon',
            props: ['icon'],
            template: '<button><slot /></button>',
          },
          VMenu: {
            template:
              '<div><slot name="activator" :props="{}" /><slot /></div>',
          },
          VList: { template: '<div><slot /></div>' },
        },
      },
    })

    expect(wrapper.findComponent({ name: 'VBtnIcon' }).props('icon')).toBe(
      mdiDotsVertical
    )

    const listItems = wrapper.findAllComponents({ name: 'VListItem' })
    const siteLink = listItems.find(
      (item) => item.props('title') === 'View on site details page'
    )
    const visualizeLink = listItems.find(
      (item) => item.props('title') === 'View on visualize data page'
    )

    expect(siteLink?.props('to')).toEqual({
      name: 'SiteDetails',
      params: { id: 'site-1' },
      query: { datastream: 'datastream-1' },
    })
    expect(visualizeLink?.props('to')).toEqual({
      name: 'VisualizeData',
      query: {
        sites: 'site-1',
        datastreams: 'datastream-1',
      },
    })
  })
})
