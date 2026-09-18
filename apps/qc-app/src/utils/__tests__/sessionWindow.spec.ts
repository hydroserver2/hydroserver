import { describe, it, expect } from 'vitest'
import {
  committedExtent,
  defaultSessionWindow,
  validateSessionWindow,
} from '@/utils/sessionWindow'

const source = {
  phenomenonBeginTime: '2025-01-01T00:00:00Z',
  phenomenonEndTime: '2025-12-31T00:00:00Z',
}
const committed = (start: string, end: string) => ({
  status: 'committed',
  phenomenonTimeStart: start,
  phenomenonTimeEnd: end,
})
const win = (begin: string, end: string) => ({
  begin: new Date(begin),
  end: new Date(end),
})

describe('committedExtent', () => {
  it('spans the earliest committed start to the latest committed end', () => {
    const extent = committedExtent([
      committed('2025-03-01T00:00:00Z', '2025-04-01T00:00:00Z'),
      committed('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'),
      { status: 'in_progress', phenomenonTimeStart: '2025-06-01T00:00:00Z', phenomenonTimeEnd: '2025-07-01T00:00:00Z' },
    ])
    expect(extent).toEqual(win('2025-01-01T00:00:00Z', '2025-04-01T00:00:00Z'))
  })

  it('is null when nothing is committed', () => {
    expect(committedExtent([])).toBeNull()
  })
})

describe('defaultSessionWindow', () => {
  it('covers the whole source when nothing is committed', () => {
    expect(defaultSessionWindow(source, [])).toEqual(
      win('2025-01-01T00:00:00Z', '2025-12-31T00:00:00Z')
    )
  })

  it('starts at the end of the committed history', () => {
    const sessions = [committed('2025-01-01T00:00:00Z', '2025-05-01T00:00:00Z')]
    expect(defaultSessionWindow(source, sessions)).toEqual(
      win('2025-05-01T00:00:00Z', '2025-12-31T00:00:00Z')
    )
  })

  it('covers the whole source when history already reaches its end', () => {
    const sessions = [committed('2025-01-01T00:00:00Z', '2025-12-31T00:00:00Z')]
    expect(defaultSessionWindow(source, sessions)).toEqual(
      win('2025-01-01T00:00:00Z', '2025-12-31T00:00:00Z')
    )
  })

  it('is null when the source has no observations', () => {
    expect(defaultSessionWindow({}, [])).toBeNull()
  })
})

describe('validateSessionWindow', () => {
  const history = [committed('2025-03-01T00:00:00Z', '2025-06-01T00:00:00Z')]

  it('accepts a window that starts exactly at the history end', () => {
    expect(
      validateSessionWindow(win('2025-06-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, history)
    ).toBeNull()
  })

  it('accepts a window overlapping committed sessions', () => {
    expect(
      validateSessionWindow(win('2025-05-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, history)
    ).toBeNull()
  })

  it('accepts a window that ends exactly at the history start', () => {
    expect(
      validateSessionWindow(win('2025-01-01T00:00:00Z', '2025-03-01T00:00:00Z'), source, history)
    ).toBeNull()
  })

  it('rejects a gap after the history', () => {
    expect(
      validateSessionWindow(win('2025-07-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, history)
    ).toMatch(/gap after/)
  })

  it('rejects a gap before the history', () => {
    expect(
      validateSessionWindow(win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'), source, history)
    ).toMatch(/gap before/)
  })

  it('rejects a window past the source end', () => {
    expect(
      validateSessionWindow(win('2025-06-01T00:00:00Z', '2026-02-01T00:00:00Z'), source, history)
    ).toMatch(/source data/)
  })

  it('rejects a start that is not before the end', () => {
    expect(
      validateSessionWindow(win('2025-08-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, [])
    ).toMatch(/before the end/)
  })

  it('accepts any in-source window when nothing is committed', () => {
    expect(
      validateSessionWindow(win('2025-09-01T00:00:00Z', '2025-10-01T00:00:00Z'), source, [])
    ).toBeNull()
  })
})
