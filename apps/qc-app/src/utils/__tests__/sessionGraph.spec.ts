import { describe, it, expect } from 'vitest'
import { commitOrder } from '@/utils/sessionGraph'

describe('commitOrder', () => {
  it('falls back to createdAt when committedAt is missing', () => {
    expect(commitOrder({ createdAt: '2025-01-01T00:00:00Z' })).toBe(
      '2025-01-01T00:00:00Z',
    )
  })
})
