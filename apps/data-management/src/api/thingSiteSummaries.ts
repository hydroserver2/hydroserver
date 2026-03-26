import hs from '@hydroserver/client'
import type { ThingSiteSummary } from '@/types'

const apiHost = import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''
const apiBaseUrl = import.meta.env.VITE_APP_PROXY_BASE_URL || apiHost

export async function listThingSiteSummaries(
  workspaceId: string
): Promise<ThingSiteSummary[]> {
  const accessToken = await hs.session.getAccessToken()
  const query = new URLSearchParams({ workspace_id: workspaceId })
  const response = await fetch(
    `${apiBaseUrl}/api/data/things/site-summaries?${query.toString()}`,
    {
      headers: {
        Accept: 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to load thing site summaries: ${response.status}`)
  }

  return (await response.json()) as ThingSiteSummary[]
}
