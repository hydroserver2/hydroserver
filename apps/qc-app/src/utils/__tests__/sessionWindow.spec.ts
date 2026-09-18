import { describe, it, expect } from 'vitest'
import {
  committedExtent,
  defaultSessionWindow,
  sessionWindowIssue,
  sessionWindowPresets,
} from '@/utils/sessionWindow'
import { subtractMonths } from '@/utils/dateMath'
import { formatStamp } from '@/utils/time'

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
const stamp = (iso: string) => formatStamp(new Date(iso))
const message = (
  window: { begin: Date; end: Date },
  sessions: ReturnType<typeof committed>[] = []
) => sessionWindowIssue(window, source, sessions)?.message ?? null

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
    expect(defaultSessionWindow(source)).toEqual(
      win('2025-01-01T00:00:00Z', '2025-12-31T00:00:00Z')
    )
  })

  it('is null when the source has no observations', () => {
    expect(defaultSessionWindow({})).toBeNull()
  })
})

describe('the default window against the rules', () => {
  it('is valid while committed history sits inside the source', () => {
    const sessions = [committed('2025-01-01T00:00:00Z', '2025-05-01T00:00:00Z')]
    const window = defaultSessionWindow(source)!
    expect(sessionWindowIssue(window, source, sessions)).toBeNull()
  })

  it('is valid when the history already covers the whole source', () => {
    const sessions = [committed('2025-01-01T00:00:00Z', '2025-12-31T00:00:00Z')]
    const window = defaultSessionWindow(source)!
    expect(sessionWindowIssue(window, source, sessions)).toBeNull()
  })

  // The source extent can shrink away from history committed earlier, and
  // then even the full extent leaves a gap. The dialog reports it.
  it('is rejected when the committed history sits outside the source', () => {
    const sessions = [committed('2026-03-01T00:00:00Z', '2026-04-01T00:00:00Z')]
    const window = defaultSessionWindow(source)!
    expect(message(window, sessions)).toMatch(/gap before/)
  })
})

describe('sessionWindowIssue', () => {
  const history = [committed('2025-03-01T00:00:00Z', '2025-06-01T00:00:00Z')]

  it('accepts a window that starts exactly at the history end', () => {
    expect(
      sessionWindowIssue(win('2025-06-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, history)
    ).toBeNull()
  })

  it('accepts a window overlapping committed sessions', () => {
    expect(
      sessionWindowIssue(win('2025-05-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, history)
    ).toBeNull()
  })

  it('accepts a window that ends exactly at the history start', () => {
    expect(
      sessionWindowIssue(win('2025-01-01T00:00:00Z', '2025-03-01T00:00:00Z'), source, history)
    ).toBeNull()
  })

  it('rejects a gap after the history', () => {
    expect(message(win('2025-07-01T00:00:00Z', '2025-08-01T00:00:00Z'), history)).toMatch(
      /gap after/
    )
  })

  it('rejects a gap before the history', () => {
    expect(message(win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'), history)).toMatch(
      /gap before/
    )
  })

  it('rejects a window past the source end', () => {
    expect(message(win('2025-06-01T00:00:00Z', '2026-02-01T00:00:00Z'), history)).toMatch(
      /source data/
    )
  })

  it('rejects a start that is not before the end', () => {
    expect(message(win('2025-08-01T00:00:00Z', '2025-08-01T00:00:00Z'))).toMatch(
      /before the end/
    )
  })

  it('accepts any in-source window when nothing is committed', () => {
    expect(
      sessionWindowIssue(win('2025-09-01T00:00:00Z', '2025-10-01T00:00:00Z'), source, [])
    ).toBeNull()
  })

  it('reports no observations when the source has none', () => {
    const issue = sessionWindowIssue(win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'), {}, [])
    expect(issue?.kind).toBe('no-data')
    expect(issue?.fix).toBeNull()
  })
})

describe('the one-click fix', () => {
  const history = [committed('2025-03-01T00:00:00Z', '2025-06-01T00:00:00Z')]

  it('moves only the start when it falls before the source', () => {
    const issue = sessionWindowIssue(
      win('2024-06-01T00:00:00Z', '2025-08-01T00:00:00Z'),
      source,
      history
    )
    expect(issue?.kind).toBe('starts-before-source')
    expect(issue?.fix?.begin?.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(issue?.fix?.end).toBeUndefined()
    expect(issue?.fix?.label).toBe(`Start at ${stamp(source.phenomenonBeginTime)}`)
  })

  it('moves only the end when it falls past the source', () => {
    const issue = sessionWindowIssue(
      win('2025-06-01T00:00:00Z', '2026-02-01T00:00:00Z'),
      source,
      history
    )
    expect(issue?.kind).toBe('ends-after-source')
    expect(issue?.fix?.end?.toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(issue?.fix?.begin).toBeUndefined()
    expect(issue?.fix?.label).toBe(`End at ${stamp(source.phenomenonEndTime)}`)
  })

  it('moves both ends when both fall outside the source', () => {
    const issue = sessionWindowIssue(
      win('2024-06-01T00:00:00Z', '2026-02-01T00:00:00Z'),
      source,
      history
    )
    expect(issue?.kind).toBe('outside-source')
    expect(issue?.fix?.begin?.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(issue?.fix?.end?.toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(issue?.fix?.label).toBe(
      `Use ${stamp(source.phenomenonBeginTime)} to ${stamp(source.phenomenonEndTime)}`
    )
  })

  it('pulls the start back to the history end on a gap after', () => {
    const issue = sessionWindowIssue(
      win('2025-07-01T00:00:00Z', '2025-08-01T00:00:00Z'),
      source,
      history
    )
    expect(issue?.kind).toBe('gap-after-history')
    expect(issue?.fix?.begin?.toISOString()).toBe('2025-06-01T00:00:00.000Z')
    expect(issue?.fix?.end).toBeUndefined()
  })

  it('pushes the end out to the history start on a gap before', () => {
    const issue = sessionWindowIssue(
      win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'),
      source,
      history
    )
    expect(issue?.kind).toBe('gap-before-history')
    expect(issue?.fix?.end?.toISOString()).toBe('2025-03-01T00:00:00.000Z')
    expect(issue?.fix?.begin).toBeUndefined()
  })

  it('offers nothing when the start is not before the end', () => {
    expect(
      sessionWindowIssue(win('2025-08-01T00:00:00Z', '2025-08-01T00:00:00Z'), source, [])?.fix
    ).toBeNull()
  })

  // The history sits outside the source, so closing the gap would push the
  // end past the source and swap one error for another.
  it('offers nothing when the correction is itself invalid', () => {
    const issue = sessionWindowIssue(defaultSessionWindow(source)!, source, [
      committed('2026-03-01T00:00:00Z', '2026-04-01T00:00:00Z'),
    ])
    expect(issue?.kind).toBe('gap-before-history')
    expect(issue?.fix).toBeNull()
  })

  it('always yields a valid window when it is offered', () => {
    const window = win('2024-06-01T00:00:00Z', '2026-02-01T00:00:00Z')
    const fix = sessionWindowIssue(window, source, history)!.fix!
    const fixed = { begin: fix.begin ?? window.begin, end: fix.end ?? window.end }
    expect(sessionWindowIssue(fixed, source, history)).toBeNull()
  })
})

describe('sessionWindowPresets', () => {
  const ids = (sessions: ReturnType<typeof committed>[]) =>
    sessionWindowPresets(source, sessions).map((p) => p.id)

  it('offers the whole record and shorter spans anchored at its end', () => {
    expect(ids([])).toEqual(['all', '1y', '6m', '1m'])
    const presets = sessionWindowPresets(source, [])
    const all = presets.find((p) => p.id === 'all')!
    expect(all.window).toEqual(defaultSessionWindow(source))
    const month = presets.find((p) => p.id === '1m')!
    const recordEnd = new Date(source.phenomenonEndTime)
    expect(month.window.end.getTime()).toBe(recordEnd.getTime())
    expect(month.window.begin.getTime()).toBe(
      subtractMonths(recordEnd, 1).getTime()
    )
  })

  it('adds a preset starting where the committed work ends', () => {
    const sessions = [committed('2025-01-01T00:00:00Z', '2025-05-01T00:00:00Z')]
    expect(ids(sessions)).toEqual(['all', '1y', '6m', '1m', 'since'])
    const since = sessionWindowPresets(source, sessions).find((p) => p.id === 'since')!
    expect(since.window.begin.toISOString()).toBe('2025-05-01T00:00:00.000Z')
    expect(since.window.end.toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(since.disabledReason).toBeNull()
  })

  it('disables a span that would leave a gap after the committed work', () => {
    const sessions = [committed('2025-01-01T00:00:00Z', '2025-05-01T00:00:00Z')]
    const presets = sessionWindowPresets(source, sessions)
    expect(presets.find((p) => p.id === '1m')!.disabledReason).toBe(
      'Leaves a gap after the committed work'
    )
    expect(presets.find((p) => p.id === 'all')!.disabledReason).toBeNull()
  })

  it('disables a span longer than the source record', () => {
    const short = {
      phenomenonBeginTime: '2025-11-01T00:00:00Z',
      phenomenonEndTime: '2025-12-01T00:00:00Z',
    }
    const presets = sessionWindowPresets(short, [])
    expect(presets.find((p) => p.id === '1y')!.disabledReason).toBe(
      'Longer than the record'
    )
    expect(presets.find((p) => p.id === 'all')!.disabledReason).toBeNull()
  })

  it('offers nothing when the source has no observations', () => {
    expect(sessionWindowPresets({}, [])).toEqual([])
  })
})
