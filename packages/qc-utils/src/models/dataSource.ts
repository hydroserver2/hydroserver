import { Datastream } from '@/types'
import { Payload } from './payload'
import { Timestamp } from './timestamp'

export const WORKFLOW_TYPES = [
  { title: 'ETL', value: 'ETL' },
  { title: 'HydroServer aggregation', value: 'Aggregation' },
  { title: 'HydroServer virtual datastream', value: 'Virtual' },
  { title: 'Streaming Data Loader', value: 'SDL' },
] as const
export type WorkflowType = (typeof WORKFLOW_TYPES)[number]['value']

export const CSV_DELIMITER_OPTIONS = [
  { value: ',', title: 'Comma' },
  { value: '|', title: 'Pipe' },
  { value: '\t', title: 'Tab' },
  { value: ';', title: 'Semicolon' },
  { value: ' ', title: 'Space' },
] as const
export type CSVDelimiterType = (typeof CSV_DELIMITER_OPTIONS)[number]['value']

export interface PerPayloadPlaceholder {
  name: string
  type: 'perPayload'
}

export interface RunTimePlaceholder {
  name: string
  type: 'runTime'
  runTimeValue: 'startTime' | 'now'
  timestamp: Timestamp
}

export type PlaceholderVariable = PerPayloadPlaceholder | RunTimePlaceholder

export const EXTRACTOR_OPTIONS = ['HTTP', 'local'] as const
export type ExtractorType = (typeof EXTRACTOR_OPTIONS)[number]
export type ETLStep = 'extractor' | 'transformer' | 'loader'

interface BaseExtractor {
  type: ExtractorType
  sourceUri: string
  placeholderVariables: PlaceholderVariable[]
}

export interface HTTPExtractor extends BaseExtractor {
  type: 'HTTP'
}

export interface LocalFileExtractor extends BaseExtractor {
  type: 'local'
}

export type ExtractorConfig = HTTPExtractor | LocalFileExtractor

export const extractorDefaults: Record<ExtractorType, ExtractorConfig> = {
  HTTP: {
    type: 'HTTP',
    sourceUri: '',
    placeholderVariables: [],
  } as HTTPExtractor,
  local: {
    type: 'local',
    sourceUri: '',
    placeholderVariables: [],
  } as LocalFileExtractor,
}

export const TRANSFORMER_OPTIONS = ['JSON', 'CSV'] as const
export type TransformerType = (typeof TRANSFORMER_OPTIONS)[number]
export enum IdentifierType {
  Name = 'name',
  Index = 'index',
}

interface BaseTransformer {
  type: TransformerType
  timestamp: Timestamp
}

export interface JSONtransformer extends BaseTransformer {
  type: 'JSON'
  JMESPath: string
}

export interface CSVTransformer extends BaseTransformer {
  type: 'CSV'
  headerRow: number | null
  dataStartRow: number
  delimiter: CSVDelimiterType
  identifierType: IdentifierType
}

export type TransformerConfig = JSONtransformer | CSVTransformer

export const transformerDefaults: Record<TransformerType, TransformerConfig> = {
  JSON: {
    type: 'JSON',
    timestamp: {
      key: '',
      format: 'ISO8601',
      timezoneMode: 'embeddedOffset',
    },
    JMESPath: '',
  } as JSONtransformer,
  CSV: {
    type: 'CSV',
    timestamp: {
      key: '',
      format: 'ISO8601',
      timezoneMode: 'embeddedOffset',
    },
    headerRow: 1,
    dataStartRow: 2,
    delimiter: ',' as CSVDelimiterType,
    identifierType: IdentifierType.Name,
  } as CSVTransformer,
}

export const LOADER_OPTIONS = ['HydroServer'] as const
export type LoaderType = (typeof LOADER_OPTIONS)[number]

interface BaseLoaderConfig {
  type: LoaderType
}

interface HydroServerLoaderConfig extends BaseLoaderConfig {
  type: 'HydroServer'
}

export type LoaderConfig = HydroServerLoaderConfig

export const loaderDefaults: Record<LoaderType, LoaderConfig> = {
  HydroServer: {
    type: 'HydroServer',
  },
}

interface EtlConfiguration {
  type: WorkflowType
  extractor: ExtractorConfig
  transformer: TransformerConfig
  loader: LoaderConfig
  payloads: Payload[]
}

export type PartialDatastream = Pick<
  Datastream,
  | 'name'
  | 'description'
  | 'noDataValue'
  | 'valueCount'
  | 'phenomenonBeginTime'
  | 'phenomenonEndTime'
  | 'aggregationStatistic'
  | 'timeAggregationInterval'
  | 'timeAggregationIntervalUnit'
  | 'intendedTimeSpacing'
  | 'intendedTimeSpacingUnit'
>

export const DATASOURCE_STATUS_OPTIONS = [
  { color: 'green', title: 'OK' },
  { color: 'blue', title: 'Pending' },
  { color: 'red', title: 'Needs attention' },
  { color: 'orange-darken-4', title: 'Behind schedule' },
  { color: 'gray', title: 'Unknown' },
  { color: 'gray', title: 'Loading paused' },
] as const
export type StatusType = (typeof DATASOURCE_STATUS_OPTIONS)[number]['title']

export const INTERVAL_UNIT_OPTIONS = [
  { value: 'minutes', title: 'Minutes' },
  { value: 'hours', title: 'Hours' },
  { value: 'days', title: 'Days' },
]
export type IntervalUnitType = (typeof INTERVAL_UNIT_OPTIONS)[number]['value']

export interface Schedule {
  interval: number
  intervalUnits?: IntervalUnitType
  crontab?: string
  startTime?: string
  endTime?: string
}

export interface Status {
  lastRunSuccessful?: boolean
  lastRunMessage?: string
  lastRun?: string
  nextRun?: string
  paused: boolean
}

export interface OrchestrationSystem {
  name: string
  id: string
  workspaceId: string
  type: string
}

export class DataSource {
  name = ''
  settings: EtlConfiguration = {
    type: 'SDL',
    extractor: JSON.parse(JSON.stringify(extractorDefaults['local'])),
    transformer: JSON.parse(JSON.stringify(transformerDefaults['CSV'])),
    loader: JSON.parse(JSON.stringify(loaderDefaults['HydroServer'])),
    payloads: [],
  }
  id = ''
  workspaceId: string = ''
  orchestrationSystem: OrchestrationSystem = {
    id: '',
    name: '',
    workspaceId: '',
    type: '',
  }
  schedule: Schedule = {
    interval: 15,
    intervalUnits: 'minutes',
  }
  status: Status = { paused: true }
  datastreams: Datastream[] = []

  constructor(init?: Partial<DataSource>) {
    Object.assign(this, init)
  }

  switchExtractor(newType: ExtractorType) {
    this.settings.extractor = JSON.parse(
      JSON.stringify(extractorDefaults[newType])
    )
  }

  switchTransformer(newType: TransformerType) {
    this.settings.transformer = JSON.parse(
      JSON.stringify(transformerDefaults[newType])
    )
  }

  switchLoader(newType: LoaderType) {
    this.settings.loader = JSON.parse(JSON.stringify(loaderDefaults[newType]))
  }
}

export function convertDataSourceToPostObject(dataSource: DataSource) {
  return {
    name: dataSource.name,
    settings: dataSource.settings,
    workspaceId: dataSource.workspaceId,
    orchestrationSystemId: dataSource.orchestrationSystem.id,
    schedule: dataSource.schedule,
    status: dataSource.status,
  }
}

export function getStatusText({
  lastRun,
  lastRunSuccessful,
  nextRun,
  paused,
}: Status): StatusType {
  if (paused) return 'Loading paused'
  if (!lastRun) return 'Pending'
  if (!lastRunSuccessful) return 'Needs attention'

  const next = nextRun ? new Date(nextRun) : undefined
  if (next && !Number.isNaN(next.valueOf())) {
    return next.getTime() < Date.now() ? 'Behind schedule' : 'OK'
  }

  return 'Unknown'
}

export function getBadCountText(statusArray: Status[]) {
  const badCount = statusArray.filter(
    (s) => getStatusText(s) === 'Needs attention'
  ).length
  if (!badCount) return ''
  if (badCount === 1) return '1 error'
  return `${badCount} errors`
}

export function getBehindScheduleCountText(statusArray: Status[]) {
  const behindCount = statusArray.filter(
    (s) => getStatusText(s) === 'Behind schedule'
  ).length
  if (!behindCount) return ''
  return `${behindCount} behind schedule`
}
