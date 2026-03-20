import { describe, it, expect, vi } from 'vitest'
import { useFormLogic } from '@/composables/useFormLogic'
import { Unit } from '@hydroserver/client'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import unitFixtures from '@/utils/test/fixtures/unitFixtures'

const [unit1, unit2] = unitFixtures

const defaultCreateItem = vi.fn()
const defaultUpdateItem = vi.fn()

describe('useFormLogic', () => {
  // onMounted won't work outside of the context of script setup, therefore
  // wrap composable with dummy component
  const createDummyComponent = ({
    createItem = defaultCreateItem,
    updateItem = defaultUpdateItem,
    initialUnit,
  }: {
    createItem?: typeof defaultCreateItem
    updateItem?: typeof defaultUpdateItem
    initialUnit?: Unit
  } = {}) =>
    defineComponent({
      setup() {
        return useFormLogic(createItem, updateItem, Unit, initialUnit)
      },
      template: '<div>{{item}}</div>',
    })

  it('initializes correctly without initialItem', async () => {
    const wrapper = mount(createDummyComponent())
    expect(wrapper.vm.item).toBeInstanceOf(Unit)
    expect(wrapper.vm.isEdit).toBe(false)
    expect(wrapper.vm.valid).toBe(false)
  })

  it('initializes correctly with initialItem', async () => {
    let initialUnit = new Unit()
    Object.assign(initialUnit, unit1)

    const wrapper = mount(
      createDummyComponent({
        initialUnit,
      })
    )

    await flushPromises()
    expect(wrapper.vm.item).toEqual(initialUnit)
    expect(wrapper.vm.isEdit).toBe(true)
  })

  it('does not submit when form is invalid', async () => {
    const createItem = vi.fn()
    const wrapper = mount(createDummyComponent({ createItem }))

    wrapper.vm.myForm = { validate: vi.fn().mockResolvedValue(undefined) } as any
    wrapper.vm.valid = false

    const result = await wrapper.vm.uploadItem()
    expect(result).toBeUndefined()
    expect(createItem).not.toHaveBeenCalled()
  })

  it('submits create when form is valid and no initial item exists', async () => {
    const createResult = { ...unit2 } as Unit
    const createItem = vi.fn().mockResolvedValue({ data: createResult })
    const wrapper = mount(createDummyComponent({ createItem }))

    wrapper.vm.myForm = { validate: vi.fn().mockResolvedValue(undefined) } as any
    wrapper.vm.valid = true

    const result = await wrapper.vm.uploadItem()
    expect(createItem).toHaveBeenCalledTimes(1)
    expect(result).toEqual(createResult)
  })

  it('submits update when form is valid and initial item exists', async () => {
    const initialUnit = Object.assign(new Unit(), unit1)
    const updateResult = { ...unit1, symbol: 'm2' } as Unit
    const updateItem = vi.fn().mockResolvedValue({ data: updateResult })

    const wrapper = mount(
      createDummyComponent({
        updateItem,
        initialUnit,
      })
    )
    await flushPromises()

    wrapper.vm.myForm = { validate: vi.fn().mockResolvedValue(undefined) } as any
    wrapper.vm.valid = true

    const result = await wrapper.vm.uploadItem()
    expect(updateItem).toHaveBeenCalledTimes(1)
    expect(result).toEqual(updateResult)
  })
})
