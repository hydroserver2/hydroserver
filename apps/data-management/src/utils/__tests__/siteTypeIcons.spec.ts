import { describe, expect, it } from 'vitest'
import {
  mdiGate,
  mdiGauge,
  mdiHydroPower,
  mdiMapMarkerOutline,
  mdiMapMarkerRadiusOutline,
  mdiWater,
  mdiWavesArrowRight,
} from '@mdi/js'
import { buildSiteTypeIconRules, getSiteTypeIcon } from '@/utils/siteTypeIcons'

describe('site type icons', () => {
  const rules = buildSiteTypeIconRules([
    { icon: 'water', siteTypes: ['stream'] },
    { icon: 'gauge', siteTypes: ['stream gage'] },
  ])

  it('uses the longest matching site type keyword', () => {
    expect(getSiteTypeIcon('Stream Gage', rules)).toBe(mdiGauge)
    expect(getSiteTypeIcon('Mountain stream', rules)).toBe(mdiWater)
  })

  it('ignores case and punctuation when matching', () => {
    expect(getSiteTypeIcon('STREAM-GAGE', rules)).toBe(mdiGauge)
  })

  it('supports site type names with non-ASCII characters', () => {
    const localizedRules = buildSiteTypeIconRules([
      { icon: 'water', siteTypes: ['Río'] },
    ])

    expect(getSiteTypeIcon('Estación Río', localizedRules)).toBe(mdiWater)
  })

  it.each([
    ['Reservoir Release', 'waves-arrow-right', mdiWavesArrowRight],
    ['Dry Dam Release', 'gate', mdiGate],
    ['Site', 'map-marker-radius-outline', mdiMapMarkerRadiusOutline],
    ['Hydropower', 'hydro-power', mdiHydroPower],
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
