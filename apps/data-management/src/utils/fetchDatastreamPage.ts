import hs, { type ApiResponse, type Datastream } from '@hydroserver/client'

const UUID = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i
const filterFields = [
  'workspaceId',
  'monitoringSiteId',
  'observedPropertyId',
  'unitId',
  'methodId',
  'processingLevelId',
] as const

type Query = Pick<
  NonNullable<Parameters<typeof hs.datastreams.list>[0]>,
  'q' | 'sortby' | (typeof filterFields)[number]
>

/** Preserve UUID search, which is not part of the server's full-text index. */
export async function fetchDatastreamPage(
  query: Query,
  range: { offset: number; limit: number }
): Promise<ApiResponse<Datastream[]>> {
  if (!query.q || !UUID.test(query.q))
    return hs.datastreams.list({ ...query, ...range })
  const response = await hs.datastreams.get(query.q)
  if (!response.ok && response.status !== 404) throw new Error(response.message)
  const rows =
    response.ok &&
    range.offset === 0 &&
    filterFields.every(
      (field) =>
        !query[field]?.length || query[field]!.includes(response.data[field])
    )
      ? [response.data]
      : []
  return {
    ok: true,
    status: 200,
    data: rows,
    meta: { numberMatched: rows.length },
  }
}
