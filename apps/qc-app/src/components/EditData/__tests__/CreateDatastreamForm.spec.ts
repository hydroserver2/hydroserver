import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import CreateDatastreamForm from '@/components/EditData/CreateDatastreamForm.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const source = {
  id: 's-1',
  name: 'Raw Temp',
  description: 'Raw temperature readings',
  status: 'ongoing',
  sensorId: 'sn-1',
  processingLevelId: 'pl-raw',
} as any

const processingLevels = [
  { id: 'pl-raw', definition: 'Raw' },
  { id: 'pl-qc', definition: 'Quality Controlled' },
]

const sensors = [
  { id: 'sn-1', name: 'Thermistor' },
  { id: 'sn-2', name: 'Weather station' },
]

const statuses = ['ongoing', 'complete']

const mountForm = (props: Record<string, unknown> = {}) =>
  mount(CreateDatastreamForm, {
    props: { source, processingLevels, sensors, statuses, ...props },
    global: { plugins: [createTestVuetify()] },
  })

// Every field below is a Vuetify component carrying the test id.
const field = (w: ReturnType<typeof mountForm>, testId: string) =>
  w.findComponent(`[data-testid="${testId}"]`) as VueWrapper

const levelSelect = (w: ReturnType<typeof mountForm>) =>
  field(w, 'create-processing-level')

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

  it('emits the create spec on confirm, defaulting the fields from the source', async () => {
    const w = mountForm()
    await levelSelect(w).vm.$emit('update:modelValue', 'pl-qc')
    await w.find('[data-testid="create-confirm"]').trigger('click')

    const spec = w.emitted('confirm')![0][0] as {
      source: { id: string }
      processingLevelId: string
      name?: string
      description: string
      status?: string
      sensorId: string
    }
    expect(spec.source.id).toBe('s-1')
    expect(spec.processingLevelId).toBe('pl-qc')
    expect(spec.name).toBe('Raw Temp (QC)')
    expect(spec.description).toBe('Raw temperature readings')
    expect(spec.status).toBe('ongoing')
    expect(spec.sensorId).toBe('sn-1')
  })

  it('emits the edited description, status and method', async () => {
    const w = mountForm({ defaultProcessingLevelId: 'pl-qc' })
    await field(w, 'create-description').vm.$emit('update:modelValue', 'QC pass')
    await field(w, 'create-status').vm.$emit('update:modelValue', 'complete')
    await field(w, 'create-sensor').vm.$emit('update:modelValue', 'sn-2')
    await w.find('[data-testid="create-confirm"]').trigger('click')

    const spec = w.emitted('confirm')![0][0] as {
      description: string
      status?: string
      sensorId: string
    }
    expect(spec.description).toBe('QC pass')
    expect(spec.status).toBe('complete')
    expect(spec.sensorId).toBe('sn-2')
  })

  it('requires a description, and allows an empty status', async () => {
    const w = mountForm({ defaultProcessingLevelId: 'pl-qc' })
    const confirm = () => w.find('[data-testid="create-confirm"]')

    await field(w, 'create-status').vm.$emit('update:modelValue', null)
    expect(confirm().attributes('disabled')).toBeUndefined()

    await field(w, 'create-description').vm.$emit('update:modelValue', '  ')
    expect(confirm().attributes('disabled')).toBeDefined()

    await field(w, 'create-description').vm.$emit('update:modelValue', 'QC pass')
    expect(confirm().attributes('disabled')).toBeUndefined()
    await confirm().trigger('click')
    const spec = w.emitted('confirm')![0][0] as { status?: string }
    expect(spec.status).toBeUndefined()
  })

  it('keeps the source values when the lists could not be loaded', async () => {
    const w = mountForm({
      defaultProcessingLevelId: 'pl-qc',
      sensors: [],
      statuses: [],
    })
    await w.find('[data-testid="create-confirm"]').trigger('click')
    const spec = w.emitted('confirm')![0][0] as {
      status?: string
      sensorId: string
    }
    expect(spec.status).toBe('ongoing')
    expect(spec.sensorId).toBe('sn-1')
  })

  it('uses the provided default processing level', async () => {
    const w = mountForm({ defaultProcessingLevelId: 'pl-qc' })
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

  it('ignores a remembered default not in this workspace, and stays invalid until a real level is picked', async () => {
    // A level id persisted from another workspace/backend.
    const w = mountForm({ defaultProcessingLevelId: 'pl-from-elsewhere' })
    // Stale default dropped -> confirm disabled (not submitted as-is).
    expect(
      w.find('[data-testid="create-confirm"]').attributes('disabled')
    ).toBeDefined()
    await levelSelect(w).vm.$emit('update:modelValue', 'pl-qc')
    expect(
      w.find('[data-testid="create-confirm"]').attributes('disabled')
    ).toBeUndefined()
  })

  it('adds a processing level inline and selects the new one', async () => {
    const created = { id: 'pl-new', code: 'Quality Controlled' }
    const onCreateProcessingLevel = vi.fn().mockResolvedValue(created)
    const w = mountForm({ onCreateProcessingLevel })

    // Open the inline add panel and submit a new level.
    await w.find('[data-testid="add-level-toggle"]').trigger('click')
    await w.find('[data-testid="new-level-code"] input').setValue('Quality Controlled')
    await w.find('[data-testid="new-level-save"]').trigger('click')
    await flushPromises()

    expect(onCreateProcessingLevel).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'Quality Controlled' })
    )
    // Parent appends the created level to the catalog.
    await w.setProps({ processingLevels: [...processingLevels, created] })

    // Panel collapsed, and the new level is selected -> confirm carries it.
    expect(w.find('[data-testid="new-level-code"]').exists()).toBe(false)
    await w.find('[data-testid="create-confirm"]').trigger('click')
    const spec = w.emitted('confirm')![0][0] as { processingLevelId: string }
    expect(spec.processingLevelId).toBe('pl-new')
  })

  it('blocks create and shows a warning when permissionError is set', async () => {
    const w = mountForm({
      defaultProcessingLevelId: 'pl-qc', // otherwise valid
      permissionError: 'You cannot create datastreams here.',
    })
    expect(w.find('[data-testid="create-permission-error"]').exists()).toBe(true)
    expect(w.text()).toContain('You cannot create datastreams here.')
    // Confirm stays disabled despite a valid processing level.
    expect(
      w.find('[data-testid="create-confirm"]').attributes('disabled')
    ).toBeDefined()
  })
})
