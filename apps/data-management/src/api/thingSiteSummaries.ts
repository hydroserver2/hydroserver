import type { ThingSiteSummary } from '@/types'

const apiHost = import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''

export async function listThingSiteSummaries(
  workspaceId: string
): Promise<ThingSiteSummary[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId })
  const response = await fetch(
    `${apiHost}/api/data/things/site-summaries?${query.toString()}`,
    {
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to load thing site summaries: ${response.status}`)
  }

  return (await response.json()) as ThingSiteSummary[]
}
