import { describe, it, expect } from 'vitest'
import { datastreamSummary } from '@/utils/datastreamSummary'

const ds = (overrides: Record<string, any> = {}) =>
  ({
    id: 'ds-1',
    name: 'Stream',
    valueCount: 1234,
    processingLevel: { definition: 'Quality controlled' },
    ...overrides,
  }) as any

const session = (status: string) => ({ id: 's', status }) as any

describe('datastreamSummary', () => {
  it('leads with the processing level definition', () => {
    expect(datastreamSummary(ds())).toContain('Level: Quality controlled')
  })

  it('falls back to the processing level code when there is no definition', () => {
    expect(datastreamSummary(ds({ processingLevel: { code: 'L1' } }))).toContain(
      'Level: L1'
    )
  })

  it('omits the level entirely when the datastream has none', () => {
    expect(datastreamSummary(ds({ processingLevel: undefined }))).not.toContain(
      'Level:'
    )
  })

  it('formats the observation count and treats a missing count as zero', () => {
    expect(datastreamSummary(ds())).toContain(
      `${new Intl.NumberFormat().format(1234)} obs`
    )
    expect(datastreamSummary(ds({ valueCount: undefined }))).toContain('0 obs')
  })

  it('omits sessions when none are supplied', () => {
    expect(datastreamSummary(ds())).not.toContain('session')
  })

  it('pluralizes the session count', () => {
    expect(datastreamSummary(ds(), [])).toContain('0 sessions')
    expect(datastreamSummary(ds(), [session('committed')])).toContain(
      '1 session'
    )
    expect(
      datastreamSummary(ds(), [session('committed'), session('committed')])
    ).toContain('2 sessions')
  })

  it('calls out in-progress sessions', () => {
    const summary = datastreamSummary(ds(), [
      session('committed'),
      session('in_progress'),
    ])
    expect(summary).toContain('2 sessions, 1 in progress')
  })
})
