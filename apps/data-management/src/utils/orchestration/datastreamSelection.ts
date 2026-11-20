type DatastreamReference = {
  id: string | number
}

export function isDatastreamLinked(
  datastreamId: string | number,
  linkedDatastreamIds: ReadonlySet<string>,
  draftDatastreams: readonly DatastreamReference[] | undefined,
  selectedDatastreamId: string | null | undefined
) {
  const id = String(datastreamId)
  if (linkedDatastreamIds.has(id)) return true

  return Boolean(
    id !== selectedDatastreamId &&
    draftDatastreams?.some((datastream) => String(datastream.id) === id)
  )
}
