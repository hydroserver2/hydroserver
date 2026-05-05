import { describe, expect, it } from 'vitest'
import {
  DATA_PRODUCT_TYPE_COLORS,
  TAB_META,
  TAB_TO_KIND,
  countTaskIssues,
  serviceForKind,
  taskHasIssue,
  worstDotColor,
} from '../orchestrationTabs'

describe('orchestration tab helpers', () => {
  it('maps tabs to task kinds and service clients', () => {
    expect(TAB_TO_KIND).toEqual({
      ingestion: 'etl',
      aggregation: 'dataProduct',
      quality: 'monitoring',
    })
    expect(TAB_META.aggregation.short).toBe('Aggregations & products')
    expect(DATA_PRODUCT_TYPE_COLORS['Rating curve'].text).toBe('#283593')
    expect(serviceForKind('etl')).toBeTruthy()
    expect(serviceForKind('dataProduct')).toBeTruthy()
    expect(serviceForKind('monitoring')).toBeTruthy()
  })

  it('counts issue rows and chooses the highest-priority status color', () => {
    const rows = [
      { statusSort: 'OK' },
      { statusSort: 'Behind schedule' },
      { statusSort: 'Needs attention' },
      { statusSort: 'Pending' },
    ] as any[]

    expect(taskHasIssue(rows[0])).toBe(false)
    expect(taskHasIssue(rows[1])).toBe(true)
    expect(countTaskIssues(rows)).toBe(2)
    expect(worstDotColor([])).toBe('#CAC4D0')
    expect(worstDotColor(rows)).toBe('#B71C1C')
    expect(worstDotColor([{ statusSort: 'Unexpected' }] as any)).toBe('#2E7D32')
  })
})
