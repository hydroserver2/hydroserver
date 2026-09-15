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
      ].map((name) => [name, { listAllItems: vi.fn(), delete: vi.fn() }])
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
    ['methods', MethodTable],
    ['observedProperties', ObservedPropertyTable],
    ['processingLevels', ProcessingLevelTable],
    ['units', UnitTable],
    ['resultQualifiers', ResultQualifierTable],
  ] as const)(
    'supports copying and viewing %s with no edit permission',
    async (service, component) => {
      vi.spyOn(hs[service], 'listAllItems').mockResolvedValue([record] as any)
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

  it('keeps UUIDs, supporting fields, and full details searchable', async () => {
    const table = render()
    for (const search of [
      record.id,
      ' temp ',
      record.description,
      'EXAMPLE MANUFACTURER',
    ]) {
      await table.setProps({ search })
      expect(
        table.find(`[data-testid="view-metadata-${record.id}"]`).exists()
      ).toBe(true)
    }
    await table.setProps({ search: 'No such item' })
    expect(table.text()).toContain('No data available')
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
    ['processingLevel', ['TEMP', record.description]],
    ['unit', ['Hydrology', '°C']],
    ['resultQualifier', ['TEMP', record.description]],
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
    ['method', ['Type not provided', 'Code not provided']],
    ['observedProperty', ['Type not provided', 'Code not provided']],
    ['processingLevel', ['Code not provided', 'Description not provided']],
    ['unit', ['Type not provided', 'Symbol not provided']],
    ['resultQualifier', ['Code not provided', 'Description not provided']],
  ] as const)(
    'keeps all three %s secondary fields when data is missing',
    (kind, details) => {
      const wrapper = render(MetadataItemTable, {
        kind,
        items: [{ id: record.id, type: ' ', code: '' }],
        showScope: true,
      })
      expect(
        wrapper
          .findAll('.hs-table-summary__details > li')
          .map((detail) => detail.text())
      ).toEqual([...details, 'Workspace'])
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
