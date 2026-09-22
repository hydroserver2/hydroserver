import { describe, it, expect } from 'vitest'
import {
  buildDependentsMap,
  hasDependents,
} from '@/utils/sessionGraph'
import type { SessionNode } from '@/utils/sessionGraph'

const node = (id: string, dependencyIds: string[] = []): SessionNode => ({
  id,
  dependencyIds,
})

/** A -> B -> C, a straight chain. */
const chain = [node('a'), node('b', ['a']), node('c', ['b'])]

describe('buildDependentsMap', () => {
  it('inverts dependencyIds into parent -> children', () => {
    const map = buildDependentsMap(chain)
    expect(map.get('a')).toEqual(['b'])
    expect(map.get('b')).toEqual(['c'])
    expect(map.get('c')).toBeUndefined()
  })

  it('treats a missing dependencyIds as no links', () => {
    expect(buildDependentsMap([{ id: 'a' }]).size).toBe(0)
  })
})

describe('hasDependents', () => {
  it('is true for a session others were built on', () => {
    expect(hasDependents(chain, 'a')).toBe(true)
    expect(hasDependents(chain, 'b')).toBe(true)
  })

  it('is false for a leaf', () => {
    expect(hasDependents(chain, 'c')).toBe(false)
  })
})
