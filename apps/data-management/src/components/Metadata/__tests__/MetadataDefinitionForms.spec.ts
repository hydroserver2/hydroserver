import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import { VTextField } from 'vuetify/components'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import hs, { Method, ObservedProperty, ProcessingLevel, Unit } from '@hydroserver/client'
import MethodFormCard from '../MethodFormCard.vue'
import ObservedPropertyFormCard from '../ObservedPropertyFormCard.vue'
import ProcessingLevelFormCard from '../ProcessingLevelFormCard.vue'
import UnitFormCard from '../UnitFormCard.vue'

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()
  return {
    ...actual,
    default: Object.fromEntries(
      ['methods', 'observedProperties', 'processingLevels', 'units'].map(
        (name) => [name, { create: vi.fn(), update: vi.fn() }]
      )
    ),
  }
})

const mounted: ReturnType<typeof mount>[] = []

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', class {
    observe() {}
    unobserve() {}
    disconnect() {}
  })
})

afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('metadata definition URL validation', () => {
  it.each([
    ['method', 'methods', MethodFormCard, Method],
    ['observedProperty', 'observedProperties', ObservedPropertyFormCard, ObservedProperty],
    ['processingLevel', 'processingLevels', ProcessingLevelFormCard, ProcessingLevel],
    ['unit', 'units', UnitFormCard, Unit],
  ] as const)(
    'keeps the %s edit form open for an incomplete URL and submits a corrected URL',
    async (propName, service, component, Model) => {
      const original = Object.assign(new Model(), {
        id: 'd66414cc-ff33-4e12-bbe0-2c048abd1f40',
        name: 'Custom metadata', description: 'Comments', type: 'Hydrology',
        symbol: 'm', definition: '',
      })
      const update = vi.spyOn(hs[service], 'update').mockResolvedValue({
        ok: true, data: { ...original, definition: 'https://website.com' },
      } as any)
      const wrapper = mount(component as any, {
        props: { [propName]: original },
        global: { plugins: [vuetify, createPinia()] },
      })
      mounted.push(wrapper)
      await flushPromises()
      const definition = wrapper.findAllComponents(VTextField)
        .find((field) => field.props('label') === 'Definition')!

      await definition.get('input').setValue('website.com')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(update).not.toHaveBeenCalled()
      expect(wrapper.emitted('close')).toBeUndefined()
      expect(definition.text()).toContain('Enter a URL starting with http:// or https://.')

      // A server rejection must also preserve the form for correction.
      update.mockResolvedValueOnce({ ok: false } as any)
      await definition.get('input').setValue('https://website.com')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(update).toHaveBeenCalledTimes(1)
      expect(wrapper.emitted('close')).toBeUndefined()

      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(update).toHaveBeenCalledTimes(2)
      expect(update.mock.calls[1][0].definition).toBe('https://website.com')
      expect(wrapper.emitted('updated')).toHaveLength(1)
      expect(wrapper.emitted('close')).toHaveLength(1)
    }
  )
})
