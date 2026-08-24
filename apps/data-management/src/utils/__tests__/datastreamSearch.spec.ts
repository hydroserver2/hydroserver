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
      text: 'recent',
    })
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
})
