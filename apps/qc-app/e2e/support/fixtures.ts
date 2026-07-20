/**
 * Fixture data for the mocked HydroServer backend.
 *
 * These shapes intentionally carry only the fields the QC app reads at
 * render time — enough to light up the workspace picker, datastream
 * table, plot, and every filter / edit operation. Fields the server
 * would normally include but which the app ignores (audit stamps,
 * embedded documents, etc.) are omitted to keep the fixtures small.
 */

export const WORKSPACE_ID = 'ws-qc-e2e'
export const DATASTREAM_ID = 'ds-qc-e2e'
export const UNIT_ID = 'unit-meters'
export const THING_ID = 'thing-stream'
export const PROC_LEVEL_ID = 'pl-raw'
export const OBSERVED_PROP_ID = 'op-streamflow'
export const SENSOR_ID = 'sensor-adv'

// Companion datastream fixtures used by the multi-datastream e2e
// scenarios. Different unit + observed property so the secondary
// Y-axis lights up with its own scale instead of overlaying the
// primary axis 1:1.
export const DATASTREAM_ID_B = 'ds-qc-e2e-b'
export const UNIT_ID_B = 'unit-celsius'
export const OBSERVED_PROP_ID_B = 'op-water-temp'
export const SENSOR_ID_B = 'sensor-temp'

/**
 * Synthetic-observation timing constants, anchored to "now" at module
 * load so the generated series always falls inside the QC app's default
 * `1w` time-range window. Hard-coding a literal anchor (e.g.
 * `2024-01-01`) was a footgun: as the calendar moved past the fixture,
 * the main plot — which slices by `[beginDate, endDate]` — silently
 * collapsed to an empty window even though the ContextPlot (which uses
 * all observations un-windowed) kept looking correct. Specs that build
 * custom observation series should import `FIXTURE_OBS_START_MS` and
 * derive their timestamps from it for the same reason.
 */
export const FIXTURE_OBS_SPACING_MS = 15 * 60 * 1000
export const FIXTURE_OBS_COUNT = 120
export const FIXTURE_OBS_END_MS = Date.now()
export const FIXTURE_OBS_START_MS =
  FIXTURE_OBS_END_MS - (FIXTURE_OBS_COUNT - 1) * FIXTURE_OBS_SPACING_MS
export const FIXTURE_OBS_START_ISO = new Date(FIXTURE_OBS_START_MS).toISOString()
export const FIXTURE_OBS_END_ISO = new Date(FIXTURE_OBS_END_MS).toISOString()

export const workspaces = [
  {
    id: WORKSPACE_ID,
    name: 'E2E Test Workspace',
    isPrivate: false,
    owner: { name: 'Test User', email: 'test@example.com' },
    collaboratorRole: {
      name: 'owner',
      permissions: [{ action: '*', resource: '*' }],
    },
  },
]

export const things = [
  {
    id: THING_ID,
    workspaceId: WORKSPACE_ID,
    name: 'Test Stream Site',
    description: 'An e2e test site',
    samplingFeatureCode: 'STRM-E2E',
    samplingFeatureType: 'Site',
    siteType: 'Stream',
    isPrivate: false,
  },
]

export const processingLevels = [
  {
    id: PROC_LEVEL_ID,
    workspaceId: WORKSPACE_ID,
    code: 'Raw',
    definition: 'Raw data',
    explanation: 'Unprocessed readings',
  },
]

export const observedProperties = [
  {
    id: OBSERVED_PROP_ID,
    workspaceId: WORKSPACE_ID,
    name: 'Streamflow',
    type: 'Hydrology',
    code: 'Q',
    definition: 'Stream discharge',
    description: 'Flow rate at the gauge',
  },
  {
    id: OBSERVED_PROP_ID_B,
    workspaceId: WORKSPACE_ID,
    name: 'Water Temperature',
    type: 'Hydrology',
    code: 'T',
    definition: 'Water temperature',
    description: 'In-stream water temperature',
  },
]

export const units = [
  {
    id: UNIT_ID,
    workspaceId: WORKSPACE_ID,
    name: 'cubic meters per second',
    symbol: 'm³/s',
    definition: 'SI unit of volumetric flow rate',
    type: 'Flow',
  },
  {
    id: UNIT_ID_B,
    workspaceId: WORKSPACE_ID,
    name: 'degrees Celsius',
    symbol: '°C',
    definition: 'SI unit of temperature',
    type: 'Temperature',
  },
]

export const datastreams = [
  {
    id: DATASTREAM_ID,
    workspaceId: WORKSPACE_ID,
    name: 'Streamflow Datastream',
    description: 'Synthetic sine-wave dataset for QC tests',
    observationType: 'OM_Measurement',
    aggregationStatistic: 'Continuous',
    timeAggregationInterval: 15,
    timeAggregationIntervalUnit: 'minutes',
    intendedTimeSpacing: 15,
    intendedTimeSpacingUnit: 'minutes',
    sampledMedium: 'Surface water',
    resultType: 'Time Series',
    status: 'ongoing',
    valueCount: 120,
    noDataValue: -9999,
    isPrivate: false,
    isVisible: true,
    unitId: UNIT_ID,
    thingId: THING_ID,
    processingLevelId: PROC_LEVEL_ID,
    observedPropertyId: OBSERVED_PROP_ID,
    sensorId: SENSOR_ID,
    phenomenonBeginTime: FIXTURE_OBS_START_ISO,
    phenomenonEndTime: FIXTURE_OBS_END_ISO,
    resultBeginTime: FIXTURE_OBS_START_ISO,
    resultEndTime: FIXTURE_OBS_END_ISO,
    // `expand_related: true` populates these nested objects on the
    // real server; the filter panel + table reads `ds.thing.id`,
    // `ds.observedProperty.name`, etc. without optional chaining in
    // some call sites, so omitting them triggers render-time throws
    // that blank out the whole table.
    thing: {
      id: THING_ID,
      name: 'Test Stream Site',
      samplingFeatureCode: 'STRM-E2E',
      samplingFeatureType: 'Site',
      siteType: 'Stream',
    },
    observedProperty: {
      id: OBSERVED_PROP_ID,
      name: 'Streamflow',
      code: 'Q',
      definition: 'Stream discharge',
      type: 'Hydrology',
    },
    processingLevel: {
      id: PROC_LEVEL_ID,
      code: 'Raw',
      definition: 'Raw data',
      explanation: 'Unprocessed readings',
    },
    unit: {
      id: UNIT_ID,
      name: 'cubic meters per second',
      symbol: 'm³/s',
      definition: 'SI unit of volumetric flow rate',
      type: 'Flow',
    },
  },
  {
    id: DATASTREAM_ID_B,
    workspaceId: WORKSPACE_ID,
    name: 'Water Temperature Datastream',
    description: 'Synthetic cosine-wave temperature for multi-axis tests',
    observationType: 'OM_Measurement',
    aggregationStatistic: 'Continuous',
    timeAggregationInterval: 15,
    timeAggregationIntervalUnit: 'minutes',
    intendedTimeSpacing: 15,
    intendedTimeSpacingUnit: 'minutes',
    sampledMedium: 'Surface water',
    resultType: 'Time Series',
    status: 'ongoing',
    valueCount: 120,
    noDataValue: -9999,
    isPrivate: false,
    isVisible: true,
    unitId: UNIT_ID_B,
    thingId: THING_ID,
    processingLevelId: PROC_LEVEL_ID,
    observedPropertyId: OBSERVED_PROP_ID_B,
    sensorId: SENSOR_ID_B,
    phenomenonBeginTime: FIXTURE_OBS_START_ISO,
    phenomenonEndTime: FIXTURE_OBS_END_ISO,
    resultBeginTime: FIXTURE_OBS_START_ISO,
    resultEndTime: FIXTURE_OBS_END_ISO,
    thing: {
      id: THING_ID,
      name: 'Test Stream Site',
      samplingFeatureCode: 'STRM-E2E',
      samplingFeatureType: 'Site',
      siteType: 'Stream',
    },
    observedProperty: {
      id: OBSERVED_PROP_ID_B,
      name: 'Water Temperature',
      code: 'T',
      definition: 'Water temperature',
      type: 'Hydrology',
    },
    processingLevel: {
      id: PROC_LEVEL_ID,
      code: 'Raw',
      definition: 'Raw data',
      explanation: 'Unprocessed readings',
    },
    unit: {
      id: UNIT_ID_B,
      name: 'degrees Celsius',
      symbol: '°C',
      definition: 'SI unit of temperature',
      type: 'Temperature',
    },
  },
]

/**
 * Generate a deterministic, well-shaped synthetic observation set:
 * `count` samples at 15-minute spacing starting at `startMs`, with
 * values following `y = 10 + 5 * sin(i / 5)` so every filter op has
 * interesting but predictable points to select. The default anchor is
 * `FIXTURE_OBS_START_MS` (relative to "now") so the series always lies
 * inside the QC app's default `1w` time-range window.
 */
export function buildObservations(
  count = FIXTURE_OBS_COUNT,
  startMs = FIXTURE_OBS_START_MS
) {
  const phenomenonTime: string[] = new Array(count)
  const result: number[] = new Array(count)
  for (let i = 0; i < count; i++) {
    phenomenonTime[i] = new Date(startMs + i * FIXTURE_OBS_SPACING_MS).toISOString()
    result[i] = +(10 + 5 * Math.sin(i / 5)).toFixed(3)
  }
  return { phenomenonTime, result }
}

/**
 * Companion series for the multi-datastream e2e scenarios. Same time
 * grid as `buildObservations`, but on a temperature-like scale and
 * offset cosine wave so a stacked render shows two visually distinct
 * curves on independent Y axes.
 */
export function buildTemperatureObservations(
  count = FIXTURE_OBS_COUNT,
  startMs = FIXTURE_OBS_START_MS
) {
  const phenomenonTime: string[] = new Array(count)
  const result: number[] = new Array(count)
  for (let i = 0; i < count; i++) {
    phenomenonTime[i] = new Date(startMs + i * FIXTURE_OBS_SPACING_MS).toISOString()
    result[i] = +(18 + 2 * Math.cos(i / 8)).toFixed(3)
  }
  return { phenomenonTime, result }
}

export const session = {
  status: 200,
  data: {
    user: {
      id: 'user-e2e',
      email: 'test@example.com',
      name: 'Test User',
    },
  },
  meta: {
    is_authenticated: true,
    session_token: 'e2e-session-token',
  },
}

export const resultQualifiers = [
  {
    id: 'rq-a',
    workspaceId: WORKSPACE_ID,
    code: 'A',
    description: 'Approved',
  },
  {
    id: 'rq-b',
    workspaceId: WORKSPACE_ID,
    code: 'B',
    description: 'Borderline',
  },
]

export const sensors = [
  {
    id: SENSOR_ID,
    workspaceId: WORKSPACE_ID,
    name: 'ADVelocity Sensor',
    description: 'Synthetic sensor for tests',
    manufacturer: 'E2E',
    model: 'TestADV',
    methodType: 'Instrument',
    methodCode: 'ADV-01',
  },
  {
    id: SENSOR_ID_B,
    workspaceId: WORKSPACE_ID,
    name: 'Thermistor Sensor',
    description: 'Synthetic temperature sensor for tests',
    manufacturer: 'E2E',
    model: 'TestTHERM',
    methodType: 'Instrument',
    methodCode: 'THERM-01',
  },
]
