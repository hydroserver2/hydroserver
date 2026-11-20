import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchDatastreamPage } from '../fetchDatastreamPage'

const { get, list } = vi.hoisted(() => ({ get: vi.fn(), list: vi.fn() }))
vi.mock('@hydroserver/client', () => ({
  default: { datastreams: { get, list } },
}))
const id = '00000000-0000-0000-0000-000000000001'
const range = { offset: 0, limit: 25 }

describe('fetchDatastreamPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('uses the list endpoint for server search, filters and paging', async () => {
    list.mockResolvedValue({ ok: true, data: [] })
    const query = { q: 'temperature', monitoringSiteId: ['site'] }
    await fetchDatastreamPage(query, range)
    expect(list).toHaveBeenCalledWith({ ...query, ...range })
    expect(get).not.toHaveBeenCalled()
  })

  it('looks up UUIDs directly while respecting the selected filters', async () => {
    const row = { id, monitoringSiteId: 'site', unitId: 'celsius' }
    get.mockResolvedValue({ ok: true, data: row })
    expect(
      (await fetchDatastreamPage({ q: id, monitoringSiteId: ['site'] }, range))
        .data
    ).toEqual([row])
    expect(
      (await fetchDatastreamPage({ q: id, monitoringSiteId: ['other'] }, range))
        .data
    ).toEqual([])
    expect(
      (await fetchDatastreamPage({ q: id, unitId: ['kelvin'] }, range)).data
    ).toEqual([])
    expect(list).not.toHaveBeenCalled()
  })

  it('returns no rows for missing UUIDs and surfaces retryable API failures', async () => {
    get
      .mockResolvedValueOnce({ ok: false, status: 404, message: 'Missing' })
      .mockResolvedValueOnce({ ok: false, status: 503, message: 'Unavailable' })
    expect((await fetchDatastreamPage({ q: id }, range)).data).toEqual([])
    await expect(fetchDatastreamPage({ q: id }, range)).rejects.toThrow(
      'Unavailable'
    )
  })
})
