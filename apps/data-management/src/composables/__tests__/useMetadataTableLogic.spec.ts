import { effectScope, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useMetadataTableLogic } from '../useMetadataTableLogic'

const notify = vi.hoisted(() => vi.fn())
vi.mock('@/utils/notifications', () => ({ Snackbar: { error: notify } }))
class MetadataRow {
  id = ''
  workspaceId: string | null = null
}
const row = { id: 'row', workspaceId: 'workspace' }
const response = (rows = [row]) => ({
  ok: true,
  status: 200,
  data: rows,
  meta: { numberMatched: rows.length },
})

function setup() {
  const service = {
    list: vi.fn().mockResolvedValue(response()),
    get: vi.fn(),
    delete: vi.fn(),
  }
  const scope = effectScope()
  const table = scope.run(() =>
    useMetadataTableLogic(
      service,
      MetadataRow,
      ref('workspace'),
      ref('all'),
      ref(''),
      ref(true)
    )
  )!
  return { service, scope, table }
}

describe('useMetadataTableLogic', () => {
  beforeEach(() => vi.clearAllMocks())

  it('keeps rows and the delete dialog on API failure, then refreshes after successful deletion', async () => {
    const { service, table, scope } = setup()
    await flushPromises()
    table.openDialog(table.items.value[0], 'delete')
    service.delete
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        message: 'Metadata is in use.',
      })
      .mockResolvedValueOnce({ ok: true, status: 204, data: null })
    await table.onDelete()
    expect(table.openDelete.value).toBe(true)
    expect(table.items.value).toHaveLength(1)
    expect(notify).toHaveBeenCalledWith('Metadata is in use.')
    service.list.mockResolvedValue(response([]))
    await table.onDelete()
    expect(table.openDelete.value).toBe(false)
    expect(table.items.value).toEqual([])
    expect(service.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 0, limit: 25 })
    )
    scope.stop()
  })

  it('requeries after editing so server filters and ordering are respected', async () => {
    const { service, table, scope } = setup()
    await flushPromises()
    service.list.mockResolvedValue(response([]))
    await table.onUpdate()
    expect(table.items.value).toEqual([])
    expect(service.list).toHaveBeenCalledTimes(2)
    scope.stop()
  })
})
