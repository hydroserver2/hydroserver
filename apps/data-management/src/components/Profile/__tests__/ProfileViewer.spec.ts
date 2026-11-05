import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createRouter, createMemoryHistory } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProfileViewer from '../ProfileViewer.vue'
import { fetchProfileData } from '@/services/profiles'
import { profileFixtureResponse } from '../../../../dev/profileFixtures'

vi.mock('@/services/profiles', () => ({ fetchProfileData: vi.fn() }))
vi.mock('plotly.js-dist', () => ({
  default: {
    react: vi.fn().mockResolvedValue(undefined),
    purge: vi.fn(),
    Plots: { resize: vi.fn() },
  },
}))
const oxygen = {
  id: 'profile-oxygen',
  name: 'Dissolved oxygen',
  monitoringSiteId: 'profile-demo',
} as any
const payload = () =>
  structuredClone(
    profileFixtureResponse(
      new URL(
        'http://demo/api/ogc/collections/datastreams/items/profile-oxygen/profiles'
      )
    ).body
  ) as any
async function viewer() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      {
        path: '/visualize-data',
        name: 'VisualizeData',
        component: { template: '<div />' },
      },
    ],
  })
  await router.push('/')
  const wrapper = mount(ProfileViewer, {
    props: { datastream: oxygen },
    global: { plugins: [createVuetify({ components, directives }), router] },
  })
  await flushPromises()
  return wrapper
}
beforeEach(() => {
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    }
  )
  vi.stubGlobal('visualViewport', new EventTarget())
  vi.mocked(fetchProfileData).mockResolvedValue(payload())
})
describe('ProfileViewer', () => {
  it('starts with the latest visit and permits historical visit comparison', async () => {
    const wrapper = await viewer()
    const visits = wrapper.findAll('input[type=checkbox]')
    expect((visits[0].element as HTMLInputElement).checked).toBe(true)
    await visits[2].setValue(true)
    expect(wrapper.find('[role=img]').attributes('aria-label')).toContain(
      '2 visits selected'
    )
    wrapper.unmount()
  })
  it('disables unavailable analytes, permits one companion, and exposes the same state in the visualization link', async () => {
    const wrapper = await viewer()
    await wrapper.findAll('[role=tab]')[1].trigger('click')
    await flushPromises()
    const analytes = wrapper.findAll('input[type=checkbox]')
    expect(analytes[1].attributes('disabled')).toBeDefined()
    await analytes[0].setValue(true)
    expect(analytes[2].attributes('disabled')).toBeDefined()
    expect(wrapper.find('a').attributes('href')).toContain(
      'profileAnalyte=profile-temperature'
    )
    await analytes[0].setValue(false)
    expect(analytes[2].attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })
  it('shows a recoverable request error and an empty state', async () => {
    vi.mocked(fetchProfileData).mockRejectedValueOnce(new Error('Unavailable'))
    const wrapper = await viewer()
    expect(wrapper.text()).toContain('Unavailable')
    vi.mocked(fetchProfileData).mockResolvedValueOnce({
      ...payload(),
      visits: [],
      observations: [],
    })
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Retry')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('No profile visits available')
    wrapper.unmount()
  })
  it('clears a companion when changing to a visit without that analyte', async () => {
    const wrapper = await viewer()
    await wrapper.findAll('[role=tab]')[1].trigger('click')
    wrapper
      .findComponent(components.VSelect)
      .vm.$emit('update:modelValue', '2026-07-17T16:00:00Z')
    await flushPromises()
    let analytes = wrapper.findAll('input[type=checkbox]')
    expect(analytes[1].attributes('disabled')).toBeUndefined()
    await analytes[1].setValue(true)
    expect(wrapper.find('a').attributes('href')).toContain(
      'profileAnalyte=profile-chlorophyll'
    )
    wrapper
      .findComponent(components.VSelect)
      .vm.$emit('update:modelValue', '2026-08-14T16:00:00Z')
    await flushPromises()
    analytes = wrapper.findAll('input[type=checkbox]')
    expect((analytes[1].element as HTMLInputElement).checked).toBe(false)
    expect(wrapper.find('a').attributes('href')).not.toContain(
      'profileAnalyte='
    )
    wrapper.unmount()
  })

  it('discards an older request when the primary datastream changes', async () => {
    let resolveOld!: (value: any) => void
    vi.mocked(fetchProfileData).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveOld = resolve
      })
    )
    const wrapper = await viewer()
    expect(wrapper.attributes('aria-busy')).toBe('true')
    await wrapper.setProps({
      datastream: { ...oxygen, id: 'profile-temperature', name: 'Temperature' },
    })
    await flushPromises()
    expect(wrapper.findAll('input[type=checkbox]')).toHaveLength(4)
    resolveOld({ ...payload(), visits: [] })
    await flushPromises()
    expect(wrapper.findAll('input[type=checkbox]')).toHaveLength(4)
    expect(wrapper.text()).not.toContain('No profile visits available')
    wrapper.unmount()
  })
})
