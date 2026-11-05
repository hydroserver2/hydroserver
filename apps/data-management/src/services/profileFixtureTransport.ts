/** Development-only HTTP fixture routing; installed before the SDK starts. */
const fixturePrefix = '/__fixtures/profiles'
const fixtureIds = new Set([
  'profile-demo',
  'profile-oxygen',
  'profile-temperature',
  'profile-chlorophyll',
  'profile-conductance',
  'demo-water-level',
  'profile-demo-water-level',
  'profile-demo-sonde',
  'profile-demo-raw',
])
const bootstrapPath = '/api/ogc/collections/datastreams/visualization-bootstrap'

function isFixtureRequest(url: URL) {
  const pathId = url.pathname.match(/\/items\/([^/]+)/)?.[1]
  if (pathId && fixtureIds.has(decodeURIComponent(pathId))) return true
  return ['workspaceId', 'monitoringSiteId', 'datastreamId'].some((key) => {
    const values = url.searchParams
      .getAll(key)
      .flatMap((value) => value.split(','))
    // Metadata queries also request global records using the "null" scope.
    return (
      values.includes('profile-demo') ||
      values.some((value) => fixtureIds.has(value) && key === 'datastreamId')
    )
  })
}

export function installProfileFixtureTransport(
  target: Pick<Window, 'fetch' | 'location'>
) {
  const originalFetch = target.fetch.bind(target)
  target.fetch = async (input, init) => {
    const request = input instanceof Request ? input : null
    const url = new URL(request?.url ?? String(input), target.location.origin)
    if (!url.pathname.startsWith('/api/ogc/')) return originalFetch(input, init)
    const method = (init?.method ?? request?.method ?? 'GET').toUpperCase()
    const fixtureUrl = `${fixturePrefix}${url.pathname}${url.search}`
    if (isFixtureRequest(url)) {
      // Only synthetic IDs are redirected, including writes (which return 405).
      return originalFetch(fixtureUrl, {
        method,
        signal: init?.signal ?? request?.signal,
      })
    }
    if (url.pathname.replace(/\/$/, '') !== bootstrapPath || method !== 'GET') {
      return originalFetch(input, init)
    }

    // Keep the real bootstrap and add public fixture streams at a separate site.
    const [response, fixtureResponse] = await Promise.all([
      originalFetch(input, init),
      originalFetch(`${fixturePrefix}${bootstrapPath}`, {
        signal: init?.signal ?? request?.signal,
      }).catch(() => null),
    ])
    if (!response.ok || !fixtureResponse?.ok) return response
    const [body, fixtures] = await Promise.all([
      response.clone().json(),
      fixtureResponse.json(),
    ])
    const payload = body.data && (body.meta || body.included) ? body.data : body
    for (const key of [
      'monitoringSites',
      'datastreams',
      'observedProperties',
      'processingLevels',
    ]) {
      const rows = Array.isArray(payload[key]) ? payload[key] : []
      const ids = new Set(rows.map((row: { id: string }) => row.id))
      payload[key] = [
        ...rows,
        ...fixtures[key].filter((row: { id: string }) => !ids.has(row.id)),
      ]
    }
    return new Response(JSON.stringify(body), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
