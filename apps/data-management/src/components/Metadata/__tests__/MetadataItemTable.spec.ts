import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import hs from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import MetadataItemTable from '../MetadataItemTable.vue'
import MethodTable from '../MethodTable.vue'
import ObservedPropertyTable from '../ObservedPropertyTable.vue'
import ProcessingLevelTable from '../ProcessingLevelTable.vue'
import UnitTable from '../UnitTable.vue'
import ResultQualifierTable from '../ResultQualifierTable.vue'
import MetadataTable from '../MetadataTable.vue'
import { useMetadata } from '@/store/metadata'

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()
  return {
    ...actual,
    default: Object.fromEntries(
      [
        'methods',
        'observedProperties',
        'processingLevels',
        'units',
        'resultQualifiers',
      ].map((name) => [name, { list: vi.fn(), delete: vi.fn() }])
    ),
  }
})

const record = {
  id: 'c6a04a9b-3efa-46df-8a73-49a458515881',
  name: 'Water temperature',
  code: 'TEMP',
  type: 'Hydrology',
  symbol: '°C',
  description: 'Water temperature measured at the monitoring site.',
  definition: 'https://example.org/temperature',
  sensorModel: 'Temperature sensor',
  sensorModelManufacturer: 'Example manufacturer',
  sensorModelDefinition: 'https://example.org/sensor',
}
const page = (rows: object[]) =>
  ({
    ok: true,
    status: 200,
    data: rows,
    meta: { numberMatched: rows.length },
  }) as any
const mounted: ReturnType<typeof mount>[] = []
const writeText = vi.fn()
function render(component: any = MetadataItemTable, props: object = {}) {
  const wrapper = mount(component, {
    props:
      component === MetadataItemTable
        ? {
            items: [record],
            kind: 'method',
            loading: false,
            hasMore: false,
            defaultScope: 'workspace',
            ...props,
          }
        : props,
    global: { plugins: [vuetify, createPinia()] },
  })
  mounted.push(wrapper)
  return wrapper
}

beforeEach(() => {
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  )
  vi.stubGlobal('visualViewport', {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  )
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })
  )
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  })
  writeText.mockReset().mockResolvedValue(undefined)
  vi.spyOn(Snackbar, 'success').mockImplementation(() => {})
  vi.spyOn(Snackbar, 'error').mockImplementation(() => {})
})
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('metadata table UUIDs and read-only details', () => {
  it.each([
    ['methods', MethodTable, 0],
    ['observedProperties', ObservedPropertyTable, 1],
    ['processingLevels', ProcessingLevelTable, 2],
    ['units', UnitTable, 3],
    ['resultQualifiers', ResultQualifierTable, 4],
  ] as const)(
    'loads %s pages for each scope from the server without remounting',
    async (service, component, tab) => {
      const systemRecord = {
        ...record,
        id: 'system-item',
        name: 'System metadata',
        workspaceId: null,
      }
      const workspaceRecord = { ...record, workspaceId: 'workspace-1' }
      const list = vi
        .mocked(hs[service].list)
        .mockImplementation(async (params: any) =>
          page([
            ...(params.workspaceId.includes('workspace-1')
              ? [workspaceRecord]
              : []),
            ...(params.workspaceId.includes('null') ? [systemRecord] : []),
          ])
        )
      const pinia = createPinia()
      useMetadata(pinia).tab = tab
      const wrapper = mount(MetadataTable, {
        props: { workspace: { id: 'workspace-1' } as any },
        global: { plugins: [vuetify, pinia] },
      })
      mounted.push(wrapper)
      await flushPromises()
      const tableId = wrapper.findComponent(component as any).vm.$.uid

      for (const [scope, workspaceId] of [
        ['workspace', ['workspace-1']],
        ['system', ['null']],
        ['all', ['workspace-1', 'null']],
      ] as const) {
        await wrapper
          .get(`[data-testid="metadata-scope-${scope}"]`)
          .trigger('click')
        await new Promise((resolve) => setTimeout(resolve, 300))
        await flushPromises()
        expect(list).toHaveBeenLastCalledWith(
          expect.objectContaining({ workspaceId, offset: 0, limit: 25 })
        )
        expect(wrapper.findComponent(component as any).vm.$.uid).toBe(tableId)
        const rows = wrapper
          .findComponent(MetadataItemTable as any)
          .props('items') as any[]
        expect(rows.map((row) => [row.id, row._scope])).toEqual([
          ...(scope !== 'system' ? [[record.id, 'workspace']] : []),
          ...(scope !== 'workspace' ? [['system-item', 'system']] : []),
        ])
      }
    }
  )

  it('uses the qualifier name as its title without a definition field', async () => {
    const wrapper = render(MetadataItemTable, { kind: 'resultQualifier' })
    expect(wrapper.get('.hs-table-summary__title').text()).toBe(record.name)
    await wrapper
      .get(`[data-testid="view-metadata-${record.id}"]`)
      .trigger('click')
    await flushPromises()
    const definition = document.querySelector(`a[href="${record.definition}"]`)
    expect(definition).toBeNull()
  })

  it.each([
    ['methods', MethodTable],
    ['observedProperties', ObservedPropertyTable],
    ['processingLevels', ProcessingLevelTable],
    ['units', UnitTable],
    ['resultQualifiers', ResultQualifierTable],
  ] as const)(
    'supports copying and viewing %s with no edit permission',
    async (service, component) => {
      vi.mocked(hs[service].list).mockResolvedValue(
        page([{ ...record, workspaceId: 'workspace-1' }])
      )
      const wrapper = render(component, {
        search: '',
        workspaceId: 'workspace-1',
        canEdit: false,
        canDelete: false,
      })
      await flushPromises()
      await wrapper
        .get(`[data-testid="copy-metadata-id-${record.id}"]`)
        .trigger('click')
      expect(writeText).toHaveBeenCalledWith(record.id)
      expect(
        wrapper
          .get('[aria-label="Edit metadata item unavailable"]')
          .attributes('disabled')
      ).toBeDefined()
      expect(
        wrapper
          .get('[aria-label="Delete metadata item unavailable"]')
          .attributes('disabled')
      ).toBeDefined()
      await wrapper
        .get(`[data-testid="view-metadata-${record.id}"]`)
        .trigger('click')
      await flushPromises()
      expect(document.body.textContent).toContain(record.id)
      expect(document.body.textContent).toContain(
        service === 'units' ? record.symbol : record.description
      )
      expect(document.querySelector('[role="dialog"] input')).toBeNull()
    }
  )

  it('reports clipboard success only after the write succeeds and handles failure', async () => {
    const wrapper = render()
    const button = wrapper.get(`[data-testid="copy-metadata-id-${record.id}"]`)
    writeText.mockRejectedValueOnce(new Error('Clipboard unavailable'))
    await button.trigger('click')
    await flushPromises()
    expect(Snackbar.error).toHaveBeenCalledWith('Failed to copy metadata UUID')
    expect(Snackbar.success).not.toHaveBeenCalled()
    await button.trigger('click')
    await flushPromises()
    expect(Snackbar.success).toHaveBeenCalledWith(
      'Metadata UUID copied to clipboard'
    )
  })

  it('searches metadata on the server', async () => {
    const list = vi.mocked(hs.units.list).mockResolvedValue(page([]))
    const wrapper = render(UnitTable, {
      search: '',
      workspaceId: 'workspace-1',
      canEdit: false,
      canDelete: false,
    })
    await flushPromises()
    await wrapper.setProps({ search: ' temp ' })
    await new Promise((resolve) => setTimeout(resolve, 300))
    expect(list).toHaveBeenLastCalledWith(
      expect.objectContaining({ q: 'temp', sortby: ['name'], offset: 0 })
    )
  })

  it('shows the row scope and opens complete details without navigating', async () => {
    const wrapper = render(MetadataItemTable, {
      items: [{ ...record, _scope: 'system' }],
      showScope: true,
    })
    expect(wrapper.text()).toContain('System')
    expect(wrapper.text()).not.toContain(record.id)
    expect(
      wrapper
        .findAll('.hs-table-summary__details > li')
        .map((detail) => detail.text())
    ).toEqual(['Hydrology', 'TEMP', 'System'])
    expect(wrapper.find('.hs-table-summary__heading .v-chip').exists()).toBe(
      false
    )
    await wrapper
      .get(`[data-testid="view-metadata-${record.id}"]`)
      .trigger('click')
    await flushPromises()
    const dialog = document.querySelector('[role="dialog"]')!
    expect(dialog.textContent).toContain('Method details')
    expect(
      dialog.querySelector('[aria-label="Close metadata details"]')
    ).toBeNull()
    expect(dialog.textContent).toContain(record.id)
    expect(dialog.textContent).toContain(record.sensorModelManufacturer)
    expect(dialog.querySelector('a')?.getAttribute('href')).toBe(
      record.definition
    )
    ;(
      dialog.querySelector(
        '.metadata-items__panel-actions button'
      ) as HTMLButtonElement
    ).click()
    await flushPromises()
    expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(
      false
    )
  })

  it.each([
    ['method', ['Hydrology', 'TEMP']],
    ['observedProperty', ['Hydrology', 'TEMP']],
    ['processingLevel', ['TEMP']],
    ['unit', ['Hydrology', '°C']],
    ['resultQualifier', [record.description]],
  ] as const)(
    'orders %s summary fields and shows scope last only in the all view',
    async (kind, details) => {
      const wrapper = render(MetadataItemTable, { kind })
      const summary = () =>
        wrapper
          .findAll('.hs-table-summary__details > li')
          .map((detail) => detail.text())

      for (const scope of ['workspace', 'system'] as const) {
        await wrapper.setProps({
          items: [{ ...record, _scope: scope }],
          showScope: true,
        })
        expect(summary()).toEqual([
          ...details,
          scope === 'workspace' ? 'Workspace' : 'System',
        ])

        await wrapper.setProps({ showScope: false })
        expect(summary()).toEqual(details)
      }
    }
  )

  it.each([
    ['method', ['Type not provided']],
    ['observedProperty', ['Type not provided']],
    ['processingLevel', []],
    ['unit', ['Type not provided', 'Symbol not provided']],
    ['resultQualifier', ['Description not provided']],
  ] as const)(
    'omits absent codes from %s summaries and preserves other details',
    async (kind, details) => {
      const wrapper = render(MetadataItemTable, {
        kind,
        items: [{ id: record.id, type: ' ', code: '' }],
        showScope: true,
      })
      for (const code of [undefined, null, '', '   ']) {
        for (const showScope of [true, false]) {
          await wrapper.setProps({
            items: [{ id: record.id, type: ' ', code }],
            showScope,
          })
          expect(
            wrapper
              .findAll('.hs-table-summary__details > li')
              .map((detail) => detail.text())
          ).toEqual([...details, ...(showScope ? ['Workspace'] : [])])
          expect(wrapper.find('.hs-table-summary__details').exists()).toBe(
            showScope || details.length > 0
          )
        }
      }
    }
  )

  it('preserves observed property type and code that match scope words', () => {
    const wrapper = render(MetadataItemTable, {
      kind: 'observedProperty',
      items: [{ ...record, type: 'Public', code: 'System' }],
      showScope: true,
    })
    expect(
      wrapper
        .findAll('.hs-table-summary__details > li')
        .map((detail) => detail.text())
    ).toEqual(['Public', 'System', 'Workspace'])
  })
})
