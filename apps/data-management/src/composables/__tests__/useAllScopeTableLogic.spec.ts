import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { Unit } from '@hydroserver/client'
import unitFixtures from '@/utils/test/fixtures/unitFixtures'
import { useAllScopeTableLogic } from '../useAllScopeTableLogic'

const workspaceUnits = () =>
  JSON.parse(JSON.stringify(unitFixtures)) as Unit[]
const systemUnits = () =>
  JSON.parse(JSON.stringify(unitFixtures)).map((unit: Unit) => ({
    ...unit,
    id: `system-${unit.id}`,
    workspaceId: null,
  })) as Unit[]

type CreateDummyOptions = {
  fetchWorkspace?: (workspaceId: string) => Promise<Unit[]>
  fetchSystem?: () => Promise<Unit[]>
  deleteItem?: (id: string) => Promise<void>
  workspaceId?: string | null
}

const createDummyComponent = ({
  fetchWorkspace = vi.fn().mockResolvedValue(workspaceUnits()),
  fetchSystem = vi.fn().mockResolvedValue(systemUnits()),
  deleteItem = vi.fn().mockResolvedValue(undefined),
  workspaceId = 'test-workspace',
}: CreateDummyOptions = {}) =>
  defineComponent({
    setup() {
      const workspaceIdRef = ref<string | null>(workspaceId)
      return {
        workspaceIdRef,
        ...useAllScopeTableLogic(
          fetchWorkspace,
          fetchSystem,
          deleteItem,
          Unit,
          workspaceIdRef
        ),
      }
    },
    template: '<div>{{ items }}</div>',
  })

describe('useAllScopeTableLogic', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('merges workspace and system items with their scopes', async () => {
    const fetchWorkspace = vi.fn().mockResolvedValue(workspaceUnits())
    const fetchSystem = vi.fn().mockResolvedValue(systemUnits())
    const wrapper = mount(
      createDummyComponent({ fetchWorkspace, fetchSystem })
    )
    await flushPromises()

    expect(fetchWorkspace).toHaveBeenCalledWith('test-workspace')
    expect(fetchSystem).toHaveBeenCalledOnce()
    expect(wrapper.vm.items.map((item) => item._scope)).toEqual([
      'workspace',
      'workspace',
      'system',
      'system',
    ])
  })

  it('opens edit and delete dialogs and ignores unknown dialog names', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    wrapper.vm.openDialog(wrapper.vm.items[0], 'edit')
    expect(wrapper.vm.openEdit).toBe(true)
    expect(wrapper.vm.item).toEqual(wrapper.vm.items[0])

    wrapper.vm.openDialog(wrapper.vm.items[1], 'delete')
    expect(wrapper.vm.openDelete).toBe(true)
    expect(wrapper.vm.item).toEqual(wrapper.vm.items[1])

    wrapper.vm.openEdit = false
    wrapper.vm.openDelete = false
    wrapper.vm.openDialog(wrapper.vm.items[0], 'unknown')
    expect(wrapper.vm.openEdit).toBe(false)
    expect(wrapper.vm.openDelete).toBe(false)
  })

  it('updates an existing item while preserving its scope', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()

    const original = wrapper.vm.items[0]
    wrapper.vm.onUpdate({ ...original, name: 'Updated unit' })

    expect(wrapper.vm.items[0].name).toBe('Updated unit')
    expect(wrapper.vm.items[0]._scope).toBe('workspace')
  })

  it('does not update an item that is not in the merged list', async () => {
    const wrapper = mount(createDummyComponent())
    await flushPromises()
    const originalItems = [...wrapper.vm.items]

    wrapper.vm.onUpdate({ ...wrapper.vm.items[0], id: 'missing' })

    expect(wrapper.vm.items).toEqual(originalItems)
  })

  it('deletes the selected item and closes the dialog', async () => {
    const deleteItem = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(createDummyComponent({ deleteItem }))
    await flushPromises()
    const selected = wrapper.vm.items[0]

    wrapper.vm.openDialog(selected, 'delete')
    await wrapper.vm.onDelete()

    expect(deleteItem).toHaveBeenCalledWith(selected.id)
    expect(wrapper.vm.items).not.toContainEqual(selected)
    expect(wrapper.vm.openDelete).toBe(false)
  })

  it('keeps the item and dialog open when deletion fails', async () => {
    const error = new Error('delete failed')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mount(
      createDummyComponent({
        deleteItem: vi.fn().mockRejectedValue(error),
      })
    )
    await flushPromises()
    const selected = wrapper.vm.items[0]

    wrapper.vm.openDialog(selected, 'delete')
    await wrapper.vm.onDelete()

    expect(wrapper.vm.items).toContainEqual(selected)
    expect(wrapper.vm.openDelete).toBe(true)
    expect(consoleError).toHaveBeenCalledWith(
      'Error deleting table item',
      error
    )
    consoleError.mockRestore()
  })

  it('clears items without fetching when the workspace id is empty', async () => {
    const fetchWorkspace = vi.fn().mockResolvedValue(workspaceUnits())
    const fetchSystem = vi.fn().mockResolvedValue(systemUnits())
    const wrapper = mount(
      createDummyComponent({
        fetchWorkspace,
        fetchSystem,
        workspaceId: null,
      })
    )
    await flushPromises()

    expect(fetchWorkspace).not.toHaveBeenCalled()
    expect(fetchSystem).not.toHaveBeenCalled()
    expect(wrapper.vm.items).toEqual([])
  })

  it('reloads both scopes when the workspace changes', async () => {
    const fetchWorkspace = vi.fn().mockResolvedValue(workspaceUnits())
    const fetchSystem = vi.fn().mockResolvedValue(systemUnits())
    const wrapper = mount(
      createDummyComponent({ fetchWorkspace, fetchSystem })
    )
    await flushPromises()

    wrapper.vm.workspaceIdRef = 'another-workspace'
    await flushPromises()

    expect(fetchWorkspace).toHaveBeenLastCalledWith('another-workspace')
    expect(fetchWorkspace).toHaveBeenCalledTimes(2)
    expect(fetchSystem).toHaveBeenCalledTimes(2)
  })

  it('logs fetch failures without replacing the existing list', async () => {
    const error = new Error('fetch failed')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mount(
      createDummyComponent({
        fetchWorkspace: vi.fn().mockRejectedValue(error),
      })
    )
    await flushPromises()

    expect(wrapper.vm.items).toEqual([])
    expect(consoleError).toHaveBeenCalledWith(
      'Error fetching table items',
      error
    )
    consoleError.mockRestore()
  })
})
