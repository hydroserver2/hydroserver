export const FIXED_OFFSET_TIMEZONES = [
  { title: 'UTC-12:00 (International Date Line West)', value: '-1200' },
  { title: 'UTC-11:00 (Samoa Standard Time)', value: '-1100' },
  { title: 'UTC-10:00 (Hawaii-Aleutian Standard Time)', value: '-1000' },
  { title: 'UTC-09:00 (Alaska Standard Time)', value: '-0900' },
  { title: 'UTC-08:00 (Pacific Standard Time)', value: '-0800' },
  { title: 'UTC-07:00 (Mountain Standard Time)', value: '-0700' },
  { title: 'UTC-06:00 (Central Standard Time)', value: '-0600' },
  { title: 'UTC-05:00 (Eastern Standard Time)', value: '-0500' },
  { title: 'UTC-04:30 (Venezuelan Standard Time)', value: '-0430' },
  { title: 'UTC-04:00 (Atlantic Standard Time)', value: '-0400' },
  { title: 'UTC-03:30 (Newfoundland Standard Time)', value: '-0330' },
  { title: 'UTC-03:00 (Argentina Standard Time)', value: '-0300' },
  { title: 'UTC-02:00 (Brazil Time)', value: '-0200' },
  { title: 'UTC-01:00 (Azores Standard Time)', value: '-0100' },
  { title: 'UTC+00:00 (Greenwich Mean Time)', value: '+0000' },
  { title: 'UTC+01:00 (Central European Time)', value: '+0100' },
  { title: 'UTC+02:00 (Eastern European Time)', value: '+0200' },
  { title: 'UTC+03:00 (Moscow Standard Time)', value: '+0300' },
  { title: 'UTC+03:30 (Iran Standard Time)', value: '+0330' },
  { title: 'UTC+04:00 (Azerbaijan Standard Time)', value: '+0400' },
  { title: 'UTC+04:30 (Afghanistan Time)', value: '+0430' },
  { title: 'UTC+05:00 (Pakistan Standard Time)', value: '+0500' },
  { title: 'UTC+05:30 (Indian Standard Time)', value: '+0530' },
  { title: 'UTC+05:45 (Nepal Time)', value: '+0545' },
  { title: 'UTC+06:00 (Bangladesh Standard Time)', value: '+0600' },
  { title: 'UTC+06:30 (Cocos Islands Time)', value: '+0630' },
  { title: 'UTC+07:00 (Indochina Time)', value: '+0700' },
  { title: 'UTC+08:00 (China Standard Time)', value: '+0800' },
  {
    title: 'UTC+08:45 (Australia Central Western Standard Time)',
    value: '+0845',
  },
  { title: 'UTC+09:00 (Japan Standard Time)', value: '+0900' },
  { title: 'UTC+09:30 (Australian Central Standard Time)', value: '+0930' },
  { title: 'UTC+10:00 (Australian Eastern Standard Time)', value: '+1000' },
  { title: 'UTC+10:30 (Lord Howe Standard Time)', value: '+1030' },
  { title: 'UTC+11:00 (Solomon Islands Time)', value: '+1100' },
  { title: 'UTC+11:30 (Norfolk Island Time)', value: '+1130' },
  { title: 'UTC+12:00 (Fiji Time)', value: '+1200' },
  { title: 'UTC+12:45 (Chatham Islands Time)', value: '+1245' },
  { title: 'UTC+13:00 (Tonga Time)', value: '+1300' },
  { title: 'UTC+14:00 (Line Islands Time)', value: '+1400' },
] as const
export type FixedOffsetTimezone =
  (typeof FIXED_OFFSET_TIMEZONES)[number]['value']

const WINTER = new Date('2025-01-01T00:00:00Z')
const SUMMER = new Date('2025-07-01T00:00:00Z')

function getLocaleOffset(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    timeZoneName: 'shortOffset',
  }).formatToParts(date)

  let off =
    parts.find((p) => p.type === 'timeZoneName')?.value.replace('GMT', '') || ''
  if (off === '+0' || off === '-0' || off === '') return '0'
  return off
}

export const DST_AWARE_TIMEZONES = Intl.supportedValuesOf('timeZone').map(
  (tz) => {
    const w = getLocaleOffset(WINTER, tz)
    const s = getLocaleOffset(SUMMER, tz)
    return {
      title: `${tz} (Winter ${w} / Summer ${s})`,
      value: tz,
    }
  }
)

Object.freeze(DST_AWARE_TIMEZONES)

export type DstAwareTimezone = (typeof DST_AWARE_TIMEZONES)[number]['value']

export const TIMESTAMP_FORMATS = [
  { text: 'Full ISO 8601 (YYYY-MM-DD hh:mm:ss.ssss+hh:mm)', value: 'ISO8601' },
  {
    text: 'Timezone naive (YYYY-MM-DD hh:mm:ss)',
    value: 'naive',
  },
  { text: 'Custom Format', value: 'custom' },
] as const
export type TimestampFormat = (typeof TIMESTAMP_FORMATS)[number]['value']

export type TimezoneMode =
  | 'utc' // always UTC
  | 'daylightSavings' // IANA / DST-aware
  | 'fixedOffset' // constant offset
  | 'embeddedOffset' // offset is in the ISO string itself

export interface Timestamp {
  key?: string
  format: TimestampFormat
  customFormat?: string

  /**
   * Determines how we interpret the timestamp’s timezone:
   * - `utc`:              timestamp is naive and UTC
   * - `daylightSavings`:  use an IANA zone from DST_AWARE_TIMEZONES
   * - `fixedOffset`:      use a value from FIXED_OFFSET_TIMEZONES
   * - `embeddedOffset`:   rely on the ±HH:MM in the ISO8601 string
   */
  timezoneMode: TimezoneMode
  timezone?: FixedOffsetTimezone | DstAwareTimezone
}
