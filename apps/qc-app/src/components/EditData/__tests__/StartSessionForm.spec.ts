import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import StartSessionForm from '@/components/EditData/StartSessionForm.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const mountForm = () =>
  mount(StartSessionForm, { global: { plugins: [createTestVuetify()] } })

describe('StartSessionForm', () => {
  it('disables confirm until a valid range is entered', async () => {
    const wrapper = mountForm()
    const confirm = () => wrapper.find('[data-testid="session-confirm"]')
    expect(confirm().attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="session-start"] input').setValue('2025-02-01T00:00')
    await wrapper.find('[data-testid="session-end"] input').setValue('2025-01-01T00:00') // before start
    expect(confirm().attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="session-end"] input').setValue('2025-03-01T00:00') // after start
    expect(confirm().attributes('disabled')).toBeUndefined()
  })

  it('emits the session spec on confirm', async () => {
    const wrapper = mountForm()
    await wrapper.find('[data-testid="session-start"] input').setValue('2025-01-01T00:00')
    await wrapper.find('[data-testid="session-end"] input').setValue('2025-02-01T00:00')
    await wrapper.find('[data-testid="session-description"] textarea').setValue('Jan QC')
    await wrapper.find('[data-testid="session-confirm"]').trigger('click')

    const emitted = wrapper.emitted('confirm')
    expect(emitted).toHaveLength(1)
    const spec = emitted![0][0] as {
      phenomenonTimeStart: string
      phenomenonTimeEnd: string
      description?: string
    }
    expect(typeof spec.phenomenonTimeStart).toBe('string')
    expect(new Date(spec.phenomenonTimeEnd).getTime()).toBeGreaterThan(
      new Date(spec.phenomenonTimeStart).getTime()
    )
    expect(spec.description).toBe('Jan QC')
  })

  it('emits cancel', async () => {
    const wrapper = mountForm()
    await wrapper.find('[data-testid="session-cancel"]').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
