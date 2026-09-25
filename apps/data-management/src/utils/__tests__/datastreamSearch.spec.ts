import { describe, expect, it } from 'vitest'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
} from '@/utils/datastreamSearch'

describe('datastream query search', () => {
  const qualifiers = [
    { key: 'site', values: ['Logan', 'Logan River', 'Logan River at Mendon'] },
    { key: 'workspace', values: ['Bear River'] },
  ]

  it('recognizes unquoted names with spaces and preserves trailing free text', () => {
    const parsed = parseDatastreamQuery(
      'discharge workspace:Bear River site:logan river at mendon recent sort:updated-desc',
      qualifiers
    )
    expect(parsed.filters.workspace).toEqual(['Bear River'])
    expect(parsed.filters.site).toEqual(['logan river at mendon'])
    expect(parsed.text).toBe('discharge recent')
    expect(parsed.sort).toEqual({ key: 'updated', order: 'desc' })
  })

  it('preserves explicit quotes, repeated filters, and incomplete quoted values', () => {
    const parsed = parseDatastreamQuery(
      'site:"Logan" site:Logan River site:"Logan River at',
      qualifiers
    )
    expect(parsed.filters.site).toEqual([
      'Logan',
      'Logan River',
      'Logan River at',
    ])
    expect(parsed.text).toBe('')
  })

  it('requires boundaries around qualifier keys and known values', () => {
    const parsed = parseDatastreamQuery(
      'website:Logan River site:Logan Riverside',
      qualifiers
    )
    expect(parsed.filters.site).toEqual(['Logan'])
    expect(parsed.text).toBe('website:Logan River Riverside')
  })

  it('parses qualifier tags separately from free text', () => {
    expect(
      parseDatastreamQuery(
        'workspace:"Bear River" site:logan observed-property:"Water temperature" unit:"Degrees Celsius" method:"Shielded sensor" recent'
      )
    ).toEqual({
      filters: {
        workspace: ['Bear River'],
        site: ['logan'],
        'observed-property': ['Water temperature'],
        unit: ['Degrees Celsius'],
        method: ['Shielded sensor'],
        'processing-level': [],
      },
      sort: null,
      text: 'recent',
    })
  })

  it('parses a GitHub-style sort qualifier separately from free text', () => {
    expect(parseDatastreamQuery('site:logan sort:updated-desc recent')).toEqual(
      {
        filters: {
          workspace: [],
          site: ['logan'],
          'observed-property': [],
          unit: [],
          method: [],
          'processing-level': [],
        },
        sort: { key: 'updated', order: 'desc' },
        text: 'recent',
      }
    )
  })

  it('serializes filter selections with quoted multi-word values', () => {
    expect(
      serializeDatastreamQuery(
        {
          workspace: ['Bear River'],
          site: ['logan'],
          'observed-property': ['Water temperature'],
          unit: ['Degrees Celsius'],
          method: ['Shielded sensor'],
          'processing-level': ['Quality controlled'],
        },
        'recent'
      )
    ).toBe(
      'workspace:"Bear River" site:logan observed-property:"Water temperature" unit:"Degrees Celsius" method:"Shielded sensor" processing-level:"Quality controlled" recent'
    )
  })

  it('serializes sort selections using the GitHub-style qualifier', () => {
    expect(
      serializeDatastreamQuery(
        {
          workspace: [],
          site: [],
          'observed-property': [],
          unit: [],
          method: [],
          'processing-level': [],
        },
        'recent',
        { key: 'observations', order: 'desc' }
      )
    ).toBe('sort:observations-desc recent')
  })
})
