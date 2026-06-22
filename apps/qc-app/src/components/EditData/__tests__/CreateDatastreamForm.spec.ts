import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import CreateDatastreamForm from '@/components/EditData/CreateDatastreamForm.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const source = { id: 's-1', name: 'Raw Temp', processingLevelId: 'pl-raw' } as any

const processingLevels = [
  { id: 'pl-raw', definition: 'Raw' },
  { id: 'pl-qc', definition: 'Quality Controlled' },
]

const mountForm = () =>
  mount(CreateDatastreamForm, {
    props: { source, processingLevels },
    global: { plugins: [createTestVuetify()] },
  })

const levelSelect = (w: ReturnType<typeof mountForm>) =>
  w.findComponent({ name: 'VSelect' })

describe('CreateDatastreamForm', () => {
  it('disables create until a different processing level is chosen', async () => {
    const w = mountForm()
    const confirm = () => w.find('[data-testid="create-confirm"]')
    expect(confirm().attributes('disabled')).toBeDefined()

    await levelSelect(w).vm.$emit('update:modelValue', 'pl-raw') // same as source
    expect(confirm().attributes('disabled')).toBeDefined()

    await levelSelect(w).vm.$emit('update:modelValue', 'pl-qc')
    expect(confirm().attributes('disabled')).toBeUndefined()
  })

  it('emits the create spec on confirm, defaulting the name from the source', async () => {
    const w = mountForm()
    await levelSelect(w).vm.$emit('update:modelValue', 'pl-qc')
    await w.find('[data-testid="create-confirm"]').trigger('click')

    const spec = w.emitted('confirm')![0][0] as {
      source: { id: string }
      processingLevelId: string
      name?: string
    }
    expect(spec.source.id).toBe('s-1')
    expect(spec.processingLevelId).toBe('pl-qc')
    expect(spec.name).toBe('Raw Temp (QC)')
  })

  it('uses the provided default processing level', async () => {
    const w = mount(CreateDatastreamForm, {
      props: { source, processingLevels, defaultProcessingLevelId: 'pl-qc' },
      global: { plugins: [createTestVuetify()] },
    })
    // Valid immediately since the default differs from the source's level.
    expect(w.find('[data-testid="create-confirm"]').attributes('disabled')).toBeUndefined()
    await w.find('[data-testid="create-confirm"]').trigger('click')
    const spec = w.emitted('confirm')![0][0] as { processingLevelId: string }
    expect(spec.processingLevelId).toBe('pl-qc')
  })

  it('emits cancel', async () => {
    const w = mountForm()
    await w.find('[data-testid="create-cancel"]').trigger('click')
    expect(w.emitted('cancel')).toHaveLength(1)
  })

  it('blocks create and shows a warning when permissionError is set', async () => {
    const w = mount(CreateDatastreamForm, {
      props: {
        source,
        processingLevels,
        defaultProcessingLevelId: 'pl-qc', // otherwise valid
        permissionError: 'You cannot create datastreams here.',
      },
      global: { plugins: [createTestVuetify()] },
    })
    expect(w.find('[data-testid="create-permission-error"]').exists()).toBe(true)
    expect(w.text()).toContain('You cannot create datastreams here.')
    // Confirm stays disabled despite a valid processing level.
    expect(
      w.find('[data-testid="create-confirm"]').attributes('disabled')
    ).toBeDefined()
  })
})
