import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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
      datastreams: { listAllItems: datastreamsMock },
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
    datastreamsMock.mockResolvedValue([
      { id: 'input-1', name: 'Input temperature', monitoringSiteId: 'site-2' },
      {
        id: 'output-1',
        name: 'Output temperature',
        monitoringSiteId: 'site-1',
        unit: { name: 'Degrees Celsius', symbol: '°C' },
      },
    ])
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

      expect(datastreamsMock).toHaveBeenCalledTimes(1)
      expect(sitesMock).toHaveBeenCalledTimes(1)
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

  it('fetches metadata once for a mapping view with multiple targets', async () => {
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
    expect(datastreamsMock).toHaveBeenCalledTimes(1)
    expect(sitesMock).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
})
