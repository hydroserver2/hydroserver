export interface QcEditLinkOptions {
  workspaceId: string
  datastreamId: string
}

export function buildQcEditUrl({
  workspaceId,
  datastreamId,
}: QcEditLinkOptions): string {
  const params = new URLSearchParams()
  params.set('ws', workspaceId)
  params.set('m', 'e')
  params.set('ds', datastreamId)

  return `/qc/?${params.toString()}`
}
