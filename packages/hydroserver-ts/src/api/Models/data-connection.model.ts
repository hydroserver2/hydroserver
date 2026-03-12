import { Timestamp } from '../../types/timestamp'
import type { Datastream, Workspace } from '../../types'

export class DataConnection {
  name = ''
  id = ''
  type = 'ETL'
  workspace: Workspace | null = null
  extractor: ExtractorConfig = JSON.parse(
    JSON.stringify(extractorDefaults['local'])
  )
  transformer: TransformerConfig = JSON.parse(
    JSON.stringify(transformerDefaults['CSV'])
  )
  loader: LoaderConfig = JSON.parse(
    JSON.stringify(loaderDefaults['HydroServer'])
  )

  constructor(init?: Partial<DataConnection>) {
    Object.assign(this, init)
    this.id ||= crypto.randomUUID()
  }
}

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

export interface PerTaskPlaceholder {
  name: string
  type: 'perTask'
}

export interface RunTimePlaceholder {
  name: string
  type: 'runTime'
  runTimeValue: 'startTime' | 'now'
  timestamp: Timestamp
}

export type PlaceholderVariable = PerTaskPlaceholder | RunTimePlaceholder

export const EXTRACTOR_OPTIONS = ['HTTP', 'local'] as const
export type ExtractorType = (typeof EXTRACTOR_OPTIONS)[number]

interface BaseExtractor {
  type: ExtractorType
  settings: {}
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
    settings: {
      sourceUri: '',
      placeholderVariables: [],
    },
  } as HTTPExtractor,
  local: {
    type: 'local',
    settings: {
      sourceUri: '',
      placeholderVariables: [],
    },
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
  settings: {}
}

export interface JSONtransformer extends BaseTransformer {
  type: 'JSON'
  settings: {
    JMESPath: string
  }
}

export interface CSVTransformer extends BaseTransformer {
  type: 'CSV'
  settings: {
    headerRow: number | null
    dataStartRow: number
    delimiter: CSVDelimiterType
    identifierType: IdentifierType
  }
}

export type TransformerConfig = JSONtransformer | CSVTransformer

export const transformerDefaults: Record<TransformerType, TransformerConfig> = {
  JSON: {
    type: 'JSON',
    settings: {
      timestamp: {
        key: '',
        format: 'ISO8601',
        timezoneMode: 'embeddedOffset',
      },
      JMESPath: '',
    },
  } as JSONtransformer,
  CSV: {
    type: 'CSV',
    settings: {
      timestamp: {
        key: '',
        format: 'ISO8601',
        timezoneMode: 'embeddedOffset',
      },
      headerRow: 1,
      dataStartRow: 2,
      delimiter: ',' as CSVDelimiterType,
      identifierType: IdentifierType.Name,
    },
  } as CSVTransformer,
}

export const LOADER_OPTIONS = ['HydroServer'] as const
export type LoaderType = (typeof LOADER_OPTIONS)[number]

interface BaseLoaderConfig {
  type: LoaderType
  settings: {}
}

interface HydroServerLoaderConfig extends BaseLoaderConfig {
  type: 'HydroServer'
}

export type LoaderConfig = HydroServerLoaderConfig

export const loaderDefaults: Record<LoaderType, LoaderConfig> = {
  HydroServer: {
    type: 'HydroServer',
    settings: {},
  },
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

export function switchExtractor(ds: DataConnection, newType: ExtractorType) {
  ds.extractor = JSON.parse(JSON.stringify(extractorDefaults[newType]))
}

export function switchTransformer(
  ds: DataConnection,
  newType: TransformerType
) {
  ds.transformer = JSON.parse(JSON.stringify(transformerDefaults[newType]))
}

export function switchLoader(ds: DataConnection, newType: LoaderType) {
  ds.loader = JSON.parse(JSON.stringify(loaderDefaults[newType]))
}
