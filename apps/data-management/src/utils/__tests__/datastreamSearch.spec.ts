import { describe, expect, it } from 'vitest'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
} from '@/utils/datastreamSearch'

describe('datastream query search', () => {
  it('parses qualifier tags separately from free text', () => {
    expect(
      parseDatastreamQuery(
        'workspace:"Bear River" site:logan observed-property:"Water temperature" recent'
      )
    ).toEqual({
      filters: {
        workspace: ['Bear River'],
        site: ['logan'],
        'observed-property': ['Water temperature'],
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
          'processing-level': ['Quality controlled'],
        },
        'recent'
      )
    ).toBe(
      'workspace:"Bear River" site:logan observed-property:"Water temperature" processing-level:"Quality controlled" recent'
    )
  })

  it('serializes sort selections using the GitHub-style qualifier', () => {
    expect(
      serializeDatastreamQuery(
        {
          workspace: [],
          site: [],
          'observed-property': [],
          'processing-level': [],
        },
        'recent',
        { key: 'observations', order: 'desc' }
      )
    ).toBe('sort:observations-desc recent')
  })
})
