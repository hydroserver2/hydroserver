import { describe, expect, it } from 'vitest'
import { isDatastreamLinked } from '../orchestration/datastreamSelection'

describe('isDatastreamLinked', () => {
  const draftDatastreams = [{ id: 'current' }, { id: 'other-draft' }]

  it('does not treat the current unsaved selection as linked', () => {
    expect(
      isDatastreamLinked('current', new Set(), draftDatastreams, 'current')
    ).toBe(false)
  })

  it('treats selections in other draft mappings as linked', () => {
    expect(
      isDatastreamLinked('other-draft', new Set(), draftDatastreams, 'current')
    ).toBe(true)
  })

  it('keeps persisted links linked even when they are the current selection', () => {
    expect(
      isDatastreamLinked(
        'current',
        new Set(['current']),
        draftDatastreams,
        'current'
      )
    ).toBe(true)
  })
})
