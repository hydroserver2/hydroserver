/**
 * Profiles of pages of observations, selected by URI with the `profile` query
 * parameter. Row and column profiles hold the same properties as observation
 * records, grouped by datastream; without a profile, pages hold records.
 */
export const ObservationProfile = {
  Row: 'https://hydroserver.org/profiles/observations/row',
  Column: 'https://hydroserver.org/profiles/observations/column',
} as const

export type ObservationProfile =
  (typeof ObservationProfile)[keyof typeof ObservationProfile]
