import type { Workspace } from '../../types'
import type { IntervalPeriod } from './task.model'

export type PayloadType = 'CSV' | 'JSON'
export type PlaceholderVariableType =
  | 'run_time'
  | 'latest_observation_timestamp'
  | 'per_task'
export type TimezoneType = 'offset' | 'iana'
export type CSVDelimiterType = ',' | '\t' | ';' | '|' | ' '

export interface CSVPayload {
  type: 'CSV'
  timestampKey: string
  timestampFormat?: string | null
  headerRow?: number | null
  dataStartRow?: number | null
  delimiter?: CSVDelimiterType | null
}

export interface JSONPayload {
  type: 'JSON'
  timestampKey: string
  timestampFormat?: string | null
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
  authHeaderName: string | null = null
  authHeaderValue: string | null = null
  workspace: Workspace | null = null
  timezoneType: TimezoneType | null = null
  timezone: string | null = null
  payload: Payload = { type: 'CSV', timestampKey: '' }
  placeholderVariables: PlaceholderVariable[] = []
  notification: Notification | null = null
  taskCount = 0
  taskAttentionCount = 0

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

export enum IdentifierType { Name = 'name', Index = 'index' }
