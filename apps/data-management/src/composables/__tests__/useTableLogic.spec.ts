import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { useTableLogic } from '../useTableLogic'
import { Unit } from '@hydroserver/client'
import unitFixtures from '@/utils/test/fixtures/unitFixtures'

const defaultFetchFunction = (wsId: string): Promise<Unit[]> =>
  Promise.resolve(JSON.parse(JSON.stringify(unitFixtures)))

const defaultDeleteFunction = (id: string): Promise<void> => Promise.resolve()

type CreateDummyOptions = {
  apiFetchFunction?: (wsId: string) => Promise<Unit[]>
  apiDeleteFunction?: (id: string) => Promise<void>
  workspaceId?: string | null
}

const createDummyComponent = ({
  apiFetchFunction = defaultFetchFunction,
  apiDeleteFunction = defaultDeleteFunction,
  workspaceId = 'test-workspace',
}: CreateDummyOptions = {}) =>
  defineComponent({
    setup() {
      const workspaceIdRef = ref<string | null>(workspaceId)
      return {
        workspaceIdRef,
        ...useTableLogic(
          apiFetchFunction,
          apiDeleteFunction,
          Unit,
          workspaceIdRef
        ),
      }
    },
    template: '<div>{{ items }}</div>',
  })

describe('useTableLogic', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('fetches items on component mount', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()
    expect(wrapper.vm.items).toEqual(unitFixtures)
  })

  it('opens edit dialog and sets the item correctly', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    wrapper.vm.openDialog(unitFixtures[0], 'edit')
    expect(wrapper.vm.openEdit).toBe(true)
    expect(wrapper.vm.item).toEqual(unitFixtures[0])
  })

  it('opens delete dialog and sets the item correctly', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    wrapper.vm.openDialog(unitFixtures[1], 'delete')
    expect(wrapper.vm.openDelete).toBe(true)
    expect(wrapper.vm.item).toEqual(unitFixtures[1])
  })

  it('opens access control dialog and sets the item correctly', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    wrapper.vm.openDialog(unitFixtures[2], 'accessControl')
    expect(wrapper.vm.openAccessControl).toBe(true)
    expect(wrapper.vm.item).toEqual(unitFixtures[2])
  })

  it('ignores unknown dialog values', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    wrapper.vm.openDialog(unitFixtures[0], 'unknown')
    expect(wrapper.vm.openEdit).toBe(false)
    expect(wrapper.vm.openDelete).toBe(false)
    expect(wrapper.vm.openAccessControl).toBe(false)
  })

  it('updates an item correctly', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    const updatedItem = { ...unitFixtures[0], name: 'Updated' }
    wrapper.vm.onUpdate(updatedItem)
    expect(wrapper.vm.items).toContainEqual(updatedItem)
  })

  it('does not update list when updated item id is missing', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    const originalItems = [...wrapper.vm.items]
    wrapper.vm.onUpdate({ ...unitFixtures[0], id: 'missing' })
    expect(wrapper.vm.items).toEqual(originalItems)
  })

  it('deletes an item correctly', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    wrapper.vm.openDialog(unitFixtures[0], 'delete')
    await wrapper.vm.onDelete()
    await flushPromises()

    expect(wrapper.vm.items).not.toContainEqual(unitFixtures[0])
    expect(wrapper.vm.openDelete).toBe(false)
  })

  it('keeps delete dialog open and logs when delete fails', async () => {
    const error = new Error('delete failed')
    const apiDeleteFunction = vi.fn().mockRejectedValue(error)
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    const wrapper = mount(createDummyComponent({ apiDeleteFunction }))
    await flushPromises()

    wrapper.vm.openDialog(unitFixtures[0], 'delete')
    await wrapper.vm.onDelete()

    expect(consoleErrorSpy).toHaveBeenCalled()
    expect(wrapper.vm.openDelete).toBe(true)
    consoleErrorSpy.mockRestore()
  })

  it('does not fetch data when workspace id is empty', async () => {
    const apiFetchFunction = vi.fn().mockResolvedValue(unitFixtures)
    const wrapper = mount(
      createDummyComponent({
        apiFetchFunction,
        workspaceId: null,
      })
    )
    await flushPromises()

    expect(apiFetchFunction).not.toHaveBeenCalled()
    expect(wrapper.vm.items).toEqual([])
  })

  it('logs when fetch fails', async () => {
    const error = new Error('fetch failed')
    const apiFetchFunction = vi.fn().mockRejectedValue(error)
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    mount(createDummyComponent({ apiFetchFunction }))
    await flushPromises()

    expect(consoleErrorSpy).toHaveBeenCalled()
    consoleErrorSpy.mockRestore()
  })
})
