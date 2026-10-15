/**
 * DatePickerField only reports a change when the value it shows changes.
 * The model can carry seconds the field doesn't display.
 */

import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import DatePickerField from '../DatePickerField.vue'
import { timeZoneAbbreviation, timeZoneDescription } from '@/utils/time'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const mountField = (modelValue: Date) =>
  mount(DatePickerField, {
    props: { modelValue, placeholder: 'Start date' },
    global: {
      plugins: [createTestVuetify()],
      // Render the calendar inline so the picker can be driven directly.
      stubs: { VDialog: { template: '<div><slot /></div>' } },
    },
    attachTo: document.body,
  })

describe('DatePickerField', () => {
  it('does not emit when the date field is left unchanged', async () => {
    const wrapper = mountField(new Date(2021, 5, 30, 12, 34, 56, 789))
    await wrapper.findAll('input')[0]!.trigger('blur')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    wrapper.unmount()
  })

  it('does not emit when the time field is left unchanged', async () => {
    const wrapper = mountField(new Date(2021, 5, 30, 12, 34, 56, 789))
    await wrapper.findAll('input')[1]!.trigger('blur')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    wrapper.unmount()
  })

  it('emits the new value when a different day is picked', async () => {
    const wrapper = mountField(new Date(2021, 5, 30, 12, 34, 56, 789))
    wrapper
      .findComponent({ name: 'VDatePicker' })
      .vm.$emit('update:modelValue', new Date(2021, 6, 4))
    await wrapper.vm.$nextTick()
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toHaveLength(1)
    expect((emitted![0]![0] as Date).getTime()).toBe(
      new Date(2021, 6, 4, 12, 34).getTime()
    )
    wrapper.unmount()
  })

  it('labels the time input with the zone of the shown date', () => {
    const value = new Date(2026, 6, 15, 12)
    const wrapper = mountField(value)
    const field = wrapper.find('[data-testid="date-picker-time"]')
    expect(field.text()).toContain(timeZoneAbbreviation(value))
    expect(wrapper.find('[title^="Time zone"]').attributes('title')).toBe(
      `Time zone: ${timeZoneDescription(value)}`
    )
    wrapper.unmount()
  })
})
