import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MappingDatastreamCard from '../MappingDatastreamCard.vue'
import ProductTaskSwimlanes from '../../data-products/ProductTaskSwimlanes.vue'
import RatingCurveSwimlanes from '../../data-products/RatingCurveSwimlanes.vue'
import QualityTaskMappings from '../../monitoring/QualityTaskMappings.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'

const { datastreamsMock, sitesMock, rulesMock, curvesMock } = vi.hoisted(
  () => ({
    datastreamsMock: vi.fn(),
    sitesMock: vi.fn(),
    rulesMock: vi.fn(),
    curvesMock: vi.fn(),
  })
)
vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()
  return {
    ...actual,
    default: {
      ...actual.default,
      datastreams: { getItem: datastreamsMock },
      monitoringSites: { listAllItems: sitesMock },
      monitoringRules: { listAllItems: rulesMock },
      ratingCurves: { listItemsForMonitoringSite: curvesMock },
    },
  }
})

const transformation = {
  id: 'transformation-1',
  outputDatastreamId: 'output-1',
  inputDatastreams: [{ datastreamId: 'input-1', variableName: 'x' }],
}
const cases = [
  {
    label: 'aggregation',
    component: ProductTaskSwimlanes,
    props: { taskLabel: 'aggregation', transformations: [transformation] },
  },
  {
    label: 'derivation',
    component: ProductTaskSwimlanes,
    props: { taskLabel: 'derivation', transformations: [transformation] },
  },
  {
    label: 'rating curve',
    component: RatingCurveSwimlanes,
    props: { transformations: [transformation] },
  },
  {
    label: 'quality',
    component: QualityTaskMappings,
    props: { taskId: 'quality-1' },
  },
]
const stubs = {
  'v-icon': true,
  'v-skeleton-loader': true,
  'v-menu': {
    template: '<div><slot name="activator" :props="{}" /><slot /></div>',
  },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /></div>' },
  'v-btn-icon': {
    props: ['disabled'],
    template: '<button :disabled="disabled" />',
  },
  'v-btn': { template: '<button />' },
  'v-list': { template: '<div><slot /></div>' },
  'v-list-item': {
    name: 'VListItem',
    props: ['to', 'title'],
    template: '<div>{{ title }}</div>',
  },
}

describe('non-ingestion mapping datastream cards', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    useWorkspaceStore().setWorkspaces([
      { id: 'workspace-1', name: 'Workspace' } as any,
    ])
    datastreamsMock.mockImplementation(async (id) =>
      [
        {
          id: 'input-1',
          name: 'Input temperature',
          monitoringSiteId: 'site-2',
          monitoringSite: { id: 'site-2', name: 'Input station' },
        },
        {
          id: 'output-1',
          name: 'Output temperature',
          monitoringSiteId: 'site-1',
          monitoringSite: { id: 'site-1', name: 'River station' },
          unit: { name: 'Degrees Celsius', symbol: '°C' },
        },
      ].find((row) => row.id === id)
    )
    sitesMock.mockResolvedValue([
      { id: 'site-1', name: 'River station' },
      { id: 'site-2', name: 'Input station' },
    ])
    rulesMock.mockResolvedValue([{ id: 'rule-1', datastreamId: 'output-1' }])
    curvesMock.mockResolvedValue([])
  })

  it.each(cases)(
    'loads $label source and target details on a cold view with three text lines and both links',
    async ({ label, component, props }) => {
      expect(useOrchestrationStore().workspaceDatastreams).toEqual([])
      const wrapper = mount(component as any, {
        props: { ...props, monitoringSiteId: 'fallback-site' },
        global: { stubs },
      })
      await flushPromises()

      expect(datastreamsMock).toHaveBeenCalledTimes(label === 'quality' ? 1 : 2)
      expect(sitesMock).not.toHaveBeenCalled()
      const cards = [
        {
          id: 'output-1',
          name: 'Output temperature',
          siteId: 'site-1',
          siteName: 'River station',
        },
        ...(label === 'quality'
          ? []
          : [
              {
                id: 'input-1',
                name: 'Input temperature',
                siteId: 'site-2',
                siteName: 'Input station',
              },
            ]),
      ]
      expect(wrapper.findAll('.mapping-datastream-card')).toHaveLength(
        cards.length
      )
      expect(wrapper.text()).not.toContain('Variable x')
      for (const { id, name, siteId, siteName } of cards) {
        const card = wrapper.get(`[data-testid="mapping-datastream-${id}"]`)
        expect(
          [...card.get('.mapping-datastream-card__text').element.children].map(
            (line) => line.textContent?.trim()
          )
        ).toEqual([name, `@ ${siteName}`, id])
        expect(card.text()).not.toContain('Degrees Celsius')
        expect(card.text()).not.toContain('°C')
        expect(card.get('button').element.disabled).toBe(false)
        const links: VueWrapper<any>[] = card.findAllComponents({
          name: 'VListItem',
        })
        expect(
          links
            .find((link) => link.props('title') === 'View on site details page')
            ?.props('to')
        ).toEqual({
          name: 'SiteDetails',
          params: { id: siteId },
          query: { datastream: id },
        })
        expect(
          links
            .find(
              (link) => link.props('title') === 'View on visualize data page'
            )
            ?.props('to')
        ).toEqual({
          name: 'VisualizeData',
          query: { sites: siteId, datastreams: id },
        })
      }
      wrapper.unmount()
    }
  )

  it('fetches only mapped datastreams without workspace-wide lists', async () => {
    const wrapper = mount(ProductTaskSwimlanes, {
      props: {
        taskLabel: 'aggregation',
        transformations: [
          transformation,
          { ...transformation, id: 'transformation-2' },
        ] as any,
      },
      global: { stubs },
    })
    await flushPromises()
    expect(
      wrapper.findAll('[data-testid="mapping-datastream-output-1"]')
    ).toHaveLength(2)
    expect(datastreamsMock).toHaveBeenCalledTimes(4)
    expect(
      datastreamsMock.mock.calls.every(
        ([id, options]) =>
          ['input-1', 'output-1'].includes(id) && options.expand_related
      )
    ).toBe(true)
    expect(sitesMock).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it.each([
    ['is unavailable', () => datastreamsMock.mockResolvedValue(null)],
    ['fails to load', () => datastreamsMock.mockRejectedValue(new Error('x'))],
  ])('keeps the ID and site link when a datastream %s', async (_, arrange) => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    arrange()
    const wrapper = mount(MappingDatastreamCard, {
      props: { datastreamId: 'output-1', monitoringSiteId: 'fallback-site' },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.find('v-skeleton-loader-stub').exists()).toBe(false)
    expect(
      [...wrapper.get('.mapping-datastream-card__text').element.children].map(
        (line) => line.textContent?.trim()
      )
    ).toEqual(['—', 'output-1'])
    expect(wrapper.get('button').element.disabled).toBe(false)
    wrapper.unmount()
  })

  it('ignores a response for a datastream the card no longer shows', async () => {
    let resolveFirst!: (value: unknown) => void
    datastreamsMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      })
    )
    const wrapper = mount(MappingDatastreamCard, {
      props: { datastreamId: 'input-1' },
      global: { stubs },
    })
    await wrapper.setProps({ datastreamId: 'output-1' })
    await flushPromises()
    resolveFirst({ id: 'input-1', name: 'Input temperature' })
    await flushPromises()

    expect(wrapper.text()).toContain('Output temperature')
    expect(wrapper.text()).not.toContain('Input temperature')
    wrapper.unmount()
  })

  it('keeps loading the latest request when switching back to the same datastream', async () => {
    let resolveFirst!: (value: unknown) => void
    let resolveLatest!: (value: unknown) => void
    datastreamsMock
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveFirst = resolve
        })
      )
      .mockResolvedValueOnce({ id: 'output-1', name: 'Output temperature' })
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveLatest = resolve
        })
      )
    const wrapper = mount(MappingDatastreamCard, {
      props: { datastreamId: 'input-1' },
      global: { stubs },
    })
    await wrapper.setProps({ datastreamId: 'output-1' })
    await wrapper.setProps({ datastreamId: 'input-1' })
    resolveFirst({ id: 'input-1', name: 'Stale input' })
    await flushPromises()

    expect(wrapper.attributes('aria-busy')).toBe('true')
    expect(wrapper.find('v-skeleton-loader-stub').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Stale input')
    expect(wrapper.text()).not.toContain('input-1')

    resolveLatest({
      id: 'input-1',
      name: 'Current input',
      monitoringSite: { id: 'site-2', name: 'Input station' },
    })
    await flushPromises()
    expect(wrapper.attributes('aria-busy')).toBe('false')
    expect(wrapper.find('v-skeleton-loader-stub').exists()).toBe(false)
    expect(wrapper.text()).toContain('Current input')
    expect(wrapper.text()).toContain('Input station')
    expect(wrapper.text()).toContain('input-1')
    wrapper.unmount()
  })
})
