import { describe, expect, it } from 'vitest'
import {
  mdiGate,
  mdiGauge,
  mdiHomeOutline,
  mdiHydroPower,
  mdiMapMarker,
  mdiMapMarkerOutline,
  mdiWater,
  mdiWaves,
  mdiWavesArrowRight,
} from '@mdi/js'
import { buildSiteTypeIconRules, getSiteTypeIcon } from '@/utils/siteTypeIcons'

describe('site type icons', () => {
  const rules = buildSiteTypeIconRules([
    { icon: 'water', siteTypes: ['Stream'] },
    { icon: 'gauge', siteTypes: ['Stream Gage'] },
    { icon: 'home-outline', siteTypes: ['House', 'Building'] },
    {
      icon: 'waves',
      siteTypes: [
        'Reservoir / Lake',
        'Reservoir',
        'Lake',
        'Pond',
        'Pool',
        'Impoundment',
      ],
    },
  ])

  it('prefers a perfect site type keyword match', () => {
    expect(getSiteTypeIcon('Stream Gage', rules)).toBe(mdiGauge)
    expect(getSiteTypeIcon('Stream', rules)).toBe(mdiWater)
  })

  it('ignores case and punctuation when matching', () => {
    expect(getSiteTypeIcon('STREAM-GAGE', rules)).toBe(mdiGauge)
    expect(getSiteTypeIcon('stream', rules)).toBe(mdiWater)
  })

  it('supports site type names with non-ASCII characters', () => {
    const localizedRules = buildSiteTypeIconRules([
      { icon: 'water', siteTypes: ['Río'] },
    ])

    expect(getSiteTypeIcon('Estación Río', localizedRules)).toBe(mdiWater)
  })

  it('uses single-word keyword matches when no perfect match is available', () => {
    expect(getSiteTypeIcon('Lake, Reservoir, Impoundment', rules)).toBe(mdiWaves)
    expect(getSiteTypeIcon('Mountain stream', rules)).toBe(mdiWater)
  })

  it.each([
    ['Reservoir Release', 'waves-arrow-right', mdiWavesArrowRight],
    ['Dry Dam Release', 'gate', mdiGate],
    ['Site', 'map-marker', mdiMapMarker],
    ['Hydropower', 'hydro-power', mdiHydroPower],
    ['House', 'home-outline', mdiHomeOutline],
  ])('maps the short-list site type %s', (siteType, icon, expected) => {
    const shortListRules = buildSiteTypeIconRules([
      { icon, siteTypes: [siteType] },
    ])

    expect(getSiteTypeIcon(siteType, shortListRules)).toBe(expected)
  })

  it('uses the default marker for an unmatched site type', () => {
    expect(getSiteTypeIcon('Custom installation', rules)).toBe(
      mdiMapMarkerOutline
    )
  })
})
