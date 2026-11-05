import type { Plugin } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { ProfileData } from '../src/models/profile'

const workspace = {
  id: 'profile-demo',
  name: 'Reservoir monitoring',
  isPrivate: false,
  description: 'Stakeholder demonstration using synthetic data.',
  tags: {},
}
const site = {
  id: 'profile-demo',
  workspaceId: workspace.id,
  name: 'Deer Creek Reservoir — Deep basin',
  code: 'DCR-01',
  type: 'Reservoir',
  latitude: 40.418,
  longitude: -111.506,
  elevationM: 1652,
  elevationDatum: 'NAVD88',
  country: 'United States',
  adminArea1: 'Utah',
  adminArea2: 'Wasatch',
  description:
    'Seasonal reservoir profiles collected at the deep basin station.',
  dataDisclaimer: 'Synthetic demo data.',
  isPrivate: false,
  tags: {},
}
const visits: ProfileData['visits'] = [
  {
    phenomenonTime: '2026-08-14T16:00:00Z',
    label: 'Aug 14, 2026 · 16:00 UTC',
    status: 'lab pending',
  },
  {
    phenomenonTime: '2026-07-31T16:00:00Z',
    label: 'Jul 31, 2026 · 16:00 UTC',
    status: 'sensor only',
  },
  {
    phenomenonTime: '2026-07-17T16:00:00Z',
    label: 'Jul 17, 2026 · 16:00 UTC',
    status: 'lab confirmed',
  },
  {
    phenomenonTime: '2026-06-19T16:00:00Z',
    label: 'Jun 19, 2026 · 16:00 UTC',
    status: 'sensor only',
  },
]
const definitions = [
  {
    id: 'profile-oxygen',
    name: 'Dissolved oxygen',
    unit: 'mg/L',
    values: [8.5, 8.4, 8.2, 7.9, 6.2, 3.4, 2.8, 2.1, 1.7, 1.4, 1.2],
  },
  {
    id: 'profile-temperature',
    name: 'Temperature',
    unit: '°C',
    values: [23.1, 23, 22.6, 21.8, 18.2, 13.9, 11.4, 10.5, 10.1, 9.8, 9.7],
  },
  {
    id: 'profile-chlorophyll',
    name: 'Chlorophyll-a',
    unit: 'µg/L',
    values: [4.1, 5.8, 8.3, 11.4, 9.1, 6.3, 3.1, 1.7, 1.1, 0.8, 0.6],
  },
  {
    id: 'profile-conductance',
    name: 'Specific conductance',
    unit: 'µS/cm',
    values: [410, 411, 414, 420, 434, 449, 458, 463, 467, 470, 472],
  },
]
const streams = definitions.map((item, index) => ({
  id: item.id,
  workspaceId: workspace.id,
  monitoringSiteId: site.id,
  name: `${item.name} — depth profile`,
  type: 'profileCoverage',
  zReference: 'Depth below surface',
  zUnit: 'm',
  description: 'Seasonal vertical profile at the deep basin station.',
  observedPropertyId: item.id,
  unitId: item.id,
  methodId: 'profile-demo-sonde',
  processingLevelId: 'profile-demo-raw',
  methodName: 'Multiparameter sonde',
  unitName: item.unit,
  unitSymbol: item.unit,
  sampledMedium: 'Water',
  noDataValue: -9999,
  aggregationStatistic: 'Instantaneous',
  timeAggregationInterval: 0,
  timeAggregationIntervalUnit: 'seconds',
  isPrivate: false,
  isVisible: true,
  valueCount: index === 2 ? 33 : 44,
  tags: {},
  phenomenonBeginTime: visits.at(-1)!.phenomenonTime,
  phenomenonEndTime: visits[0].phenomenonTime,
}))
const observations = definitions.flatMap((item, analyteIndex) =>
  visits.flatMap((visit, visitIndex) => {
    // Chlorophyll is missing at the newest visit; exercise unavailable analytes.
    if (analyteIndex === 2 && visitIndex === 0) return []
    return item.values.map((value, depthIndex) => ({
      datastreamId: item.id,
      phenomenonTime: visit.phenomenonTime,
      z: depthIndex * 2,
      result:
        depthIndex === 5 && visitIndex === 1
          ? null
          : Number(
              (
                value * (1 - visitIndex * 0.035) +
                Math.sin(depthIndex + visitIndex) * value * 0.02
              ).toFixed(2)
            ),
    }))
  })
)
const timeSeries = {
  ...streams[0],
  id: 'demo-water-level',
  name: 'Water level — hourly',
  type: 'timeSeriesCoverage',
  unitId: 'profile-demo-water-level',
  observedPropertyId: 'profile-demo-water-level',
  unitName: 'm',
  unitSymbol: 'm',
  valueCount: 168,
  phenomenonBeginTime: '2026-08-07T17:00:00Z',
  intendedTimeSpacing: 1,
  intendedTimeSpacingUnit: 'hours',
}
const timeSeriesObservations = Array.from({ length: 168 }, (_, index) => ({
  phenomenonTime: new Date(
    Date.parse('2026-08-07T17:00:00Z') + index * 3600000
  ).toISOString(),
  result: Number(
    (1648 + Math.sin(index / 15) * 0.2 - index * 0.002).toFixed(3)
  ),
}))
const allStreams = [...streams, timeSeries]
const metadata: Record<string, unknown[]> = {
  workspaces: [workspace],
  'monitoring-sites': [site],
  datastreams: allStreams,
  units: definitions
    .map((item) => ({
      id: item.id,
      name: item.unit,
      symbol: item.unit,
      type: 'Concentration',
      workspaceId: workspace.id,
    }))
    .concat([
      {
        id: 'profile-demo-water-level',
        name: 'm',
        symbol: 'm',
        type: 'Length',
        workspaceId: workspace.id,
      },
    ]),
  'observed-properties': definitions
    .map((item) => ({
      id: item.id,
      name: item.name,
      code: item.id,
      type: 'Water quality',
      workspaceId: workspace.id,
    }))
    .concat([
      {
        id: 'profile-demo-water-level',
        name: 'Water level',
        code: 'WL',
        type: 'Water level',
        workspaceId: workspace.id,
      },
    ]),
  'processing-levels': [
    {
      id: 'profile-demo-raw',
      name: 'Raw',
      code: '0',
      definition: 'Unprocessed field data',
      workspaceId: workspace.id,
    },
  ],
  methods: [
    {
      id: 'profile-demo-sonde',
      name: 'Multiparameter sonde',
      type: 'Instrument',
      code: 'SONDE',
      description: 'Vertical sonde cast',
      workspaceId: workspace.id,
    },
  ],
}
export function profileFixtureResponse(url: URL): {
  status: number
  body: unknown
  contentType?: string
} {
  const path = url.pathname.replace(/\/$/, '')
  const csvMatch = path.match(/\/datastreams\/items\/([^/]+)\/csv$/)
  if (csvMatch) {
    if (!allStreams.some((item) => item.id === csvMatch[1]))
      return { status: 404, body: { message: 'Datastream not found.' } }
    const rows =
      csvMatch[1] === timeSeries.id
        ? timeSeriesObservations.map(
            (item) => `${item.phenomenonTime},,${item.result}`
          )
        : observations
            .filter((item) => item.datastreamId === csvMatch[1])
            .map(
              (item) => `${item.phenomenonTime},${item.z},${item.result ?? ''}`
            )
    return {
      status: 200,
      contentType: 'text/csv',
      body: ['phenomenonTime,z,result', ...rows].join('\n'),
    }
  }
  if (path.endsWith('/observations/items')) {
    const id = url.searchParams.get('datastreamId')
    const rows =
      id === timeSeries.id
        ? timeSeriesObservations
        : observations.filter((item) => item.datastreamId === id)
    const sorted = url.searchParams.get('sortby')?.startsWith('-')
      ? [...rows].reverse()
      : rows
    return {
      status: 200,
      body: {
        data: [
          {
            datastreamId: id,
            columns: {
              phenomenonTime: sorted.map((item) => item.phenomenonTime),
              result: sorted.map((item) => item.result),
            },
          },
        ],
        meta: { next: null },
      },
    }
  }
  const profileMatch = path.match(/\/datastreams\/items\/([^/]+)\/profiles$/)
  if (profileMatch) {
    const stream = streams.find((item) => item.id === profileMatch[1])
    if (!stream)
      return { status: 404, body: { message: 'Profile datastream not found.' } }
    return {
      status: 200,
      body: {
        zReference: stream.zReference,
        zUnit: stream.zUnit,
        positiveDirection: 'down',
        visits: visits.filter((visit) =>
          observations.some(
            (point) =>
              point.datastreamId === stream.id &&
              point.phenomenonTime === visit.phenomenonTime
          )
        ),
        analytes: definitions.map((item) => ({
          datastreamId: item.id,
          name: item.name,
          unit: item.unit,
        })),
        observations,
      } satisfies ProfileData,
    }
  }
  if (path.endsWith('/visualization-bootstrap'))
    return {
      status: 200,
      body: {
        monitoringSites: [site],
        datastreams: allStreams,
        observedProperties: metadata['observed-properties'],
        processingLevels: metadata['processing-levels'],
      },
    }
  if (path.endsWith('/site-type-icons')) return { status: 200, body: [] }
  if (path.endsWith('/linked-resources')) return { status: 200, body: [] }
  const match = path.match(/\/collections\/([^/]+)\/items(?:\/([^/]+))?$/)
  if (match) {
    const rows = metadata[match[1]] ?? []
    if (match[2]) {
      const row = rows.find((item) => (item as { id: string }).id === match[2])
      return row
        ? {
            status: 200,
            body: {
              data: row,
              meta: {},
              included: {
                workspaces: [workspace],
                monitoringSites: [site],
                units: metadata.units,
                methods: metadata.methods,
                observedProperties: metadata['observed-properties'],
                processingLevels: metadata['processing-levels'],
              },
            },
          }
        : { status: 404, body: { message: 'Fixture not found.' } }
    }
    return {
      status: 200,
      body: {
        data: rows,
        meta: { next: null },
        included: {
          workspaces: [workspace],
          monitoringSites: [site],
          units: metadata.units,
          methods: metadata.methods,
          observedProperties: metadata['observed-properties'],
          processingLevels: metadata['processing-levels'],
        },
      },
    }
  }
  return { status: 404, body: { message: `No fixture endpoint for ${path}` } }
}
/** Read-only local fixture endpoints; standalone mode also supplies the demo API. */
export function profileFixturesPlugin(standalone = true): Plugin {
  const middleware = (
    req: IncomingMessage,
    res: ServerResponse,
    next: () => void
  ) => {
    const url = new URL(req.url ?? '/', 'http://localhost')
    const fixturePrefix = '/__fixtures/profiles'
    if (url.pathname.startsWith(fixturePrefix + '/api/')) {
      url.pathname = url.pathname.slice(fixturePrefix.length)
    } else if (!standalone || !url.pathname.startsWith('/api/')) {
      return next()
    }
    if (req.method !== 'GET') {
      res.writeHead(405, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ message: 'Demo fixtures are read-only.' }))
      return
    }
    const response = profileFixtureResponse(url)
    res.writeHead(response.status, {
      'Content-Type': response.contentType ?? 'application/json',
    })
    res.end(
      response.contentType === 'text/csv'
        ? String(response.body)
        : JSON.stringify(response.body)
    )
  }
  return {
    name: 'reservoir-profile-fixtures',
    configureServer(server) {
      server.middlewares.use(middleware)
    },
    configurePreviewServer(server) {
      if (standalone) server.middlewares.use(middleware)
    },
    transformIndexHtml(html) {
      if (!standalone) return html
      return html.replace(
        '</head>',
        '<script id="current-user" type="application/json">null</script></head>'
      )
    },
  }
}
