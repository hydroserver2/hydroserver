import { describe, expect, it } from 'vitest'
import { buildQcEditUrl } from '../qcLinks'

describe('buildQcEditUrl', () => {
  it('builds a same-origin QC edit-mode link for one datastream', () => {
    expect(
      buildQcEditUrl({
        workspaceId: 'workspace-1',
        datastreamId: 'datastream-1',
      })
    ).toBe('/qc/?ws=workspace-1&m=e&ds=datastream-1')
  })

  it('encodes workspace and datastream ids for query strings', () => {
    expect(
      buildQcEditUrl({
        workspaceId: 'workspace 1',
        datastreamId: 'datastream/1',
      })
    ).toBe('/qc/?ws=workspace+1&m=e&ds=datastream%2F1')
  })
})
