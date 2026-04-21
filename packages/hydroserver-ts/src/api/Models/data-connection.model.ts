import type { Workspace } from '../../types'
import type { IntervalPeriod } from './task.model'

export type PayloadType = 'CSV' | 'JSON'
export type PlaceholderVariableType =
  | 'run_time'
  | 'latest_observation_timestamp'
  | 'per_task'
export type TimezoneType = 'utc' | 'offset' | 'iana'
export type CSVDelimiterType = ',' | '\t' | ';' | '|' | ' '

export interface TimestampConfig {
  key: string
  format?: string | null
  timezoneType?: TimezoneType | null
  timezone?: string | null
}

export interface CSVPayload {
  type: 'CSV'
  headerRow?: number | null
  dataStartRow?: number | null
  delimiter?: CSVDelimiterType | null
}

export interface JSONPayload {
  type: 'JSON'
  jmespath?: string | null
}

export type Payload = CSVPayload | JSONPayload

export interface PlaceholderVariable {
  id?: string
  name: string
  type: PlaceholderVariableType
  timestampFormat?: string | null
}

export interface NotificationSchedule {
  enabled: boolean
  startTime?: string | null
  crontab?: string | null
  interval?: number | null
  intervalPeriod?: IntervalPeriod | null
  nextRunAt?: string | null
}

export interface Notification {
  schedule?: NotificationSchedule | null
  recipientEmails: string[]
}

export class DataConnection {
  id = ''
  name = ''
  description: string | null = null
  sourceUrl = ''
  workspace: Workspace | null = null
  timestamp: TimestampConfig = { key: '' }
  payload: Payload = { type: 'CSV' }
  placeholderVariables: PlaceholderVariable[] = []
  notification: Notification | null = null

  constructor(init?: Partial<DataConnection>) {
    Object.assign(this, init)
    this.id ||= crypto.randomUUID()
  }
}

export const CSV_DELIMITER_OPTIONS = [
  { value: ',', title: 'Comma' },
  { value: '|', title: 'Pipe' },
  { value: '\t', title: 'Tab' },
  { value: ';', title: 'Semicolon' },
  { value: ' ', title: 'Space' },
] as const

export const INTERVAL_UNIT_OPTIONS = [
  { value: 'minutes', title: 'Minutes' },
  { value: 'hours', title: 'Hours' },
  { value: 'days', title: 'Days' },
]
export type IntervalUnitType = (typeof INTERVAL_UNIT_OPTIONS)[number]['value']

// ---------------------------------------------------------------------------
// Legacy stubs — form components referencing the old extractor/transformer/loader
// API structure still import these. They need to be rewritten for the new API.
// ---------------------------------------------------------------------------

export const EXTRACTOR_OPTIONS = ['HTTP', 'local'] as const
export type ExtractorType = (typeof EXTRACTOR_OPTIONS)[number]

export interface HTTPExtractor { type: 'HTTP'; settings: Record<string, any> }
export interface LocalFileExtractor { type: 'local'; settings: Record<string, any> }
export type ExtractorConfig = HTTPExtractor | LocalFileExtractor

export const extractorDefaults: Record<ExtractorType, ExtractorConfig> = {
  HTTP: { type: 'HTTP', settings: { sourceUri: '', placeholderVariables: [] } },
  local: { type: 'local', settings: { sourceUri: '', placeholderVariables: [] } },
}
export function switchExtractor(ds: any, newType: ExtractorType) {
  ds.extractor = JSON.parse(JSON.stringify(extractorDefaults[newType]))
}

export const TRANSFORMER_OPTIONS = ['JSON', 'CSV'] as const
export type TransformerType = (typeof TRANSFORMER_OPTIONS)[number]

export enum IdentifierType { Name = 'name', Index = 'index' }

export interface JSONtransformer { type: 'JSON'; settings: Record<string, any> }
export interface CSVTransformer { type: 'CSV'; settings: Record<string, any> }
export type TransformerConfig = JSONtransformer | CSVTransformer

export function switchTransformer(ds: any, newType: TransformerType) {
  ds.transformer = { type: newType, settings: {} }
}

export const LOADER_OPTIONS = ['HydroServer'] as const
export type LoaderType = (typeof LOADER_OPTIONS)[number]
export type LoaderConfig = { type: LoaderType; settings: Record<string, any> }
export function switchLoader(ds: any, newType: LoaderType) {
  ds.loader = { type: newType, settings: {} }
}

export interface PerTaskPlaceholder { name: string; type: 'perTask' }
export interface RunTimePlaceholder {
  name: string
  type: 'runTime'
  runTimeValue: 'startTime' | 'now'
  timestamp?: any
}
