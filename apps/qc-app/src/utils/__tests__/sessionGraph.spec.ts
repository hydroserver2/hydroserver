import { describe, it, expect } from 'vitest'
import {
  buildDependentsMap,
  collectDeletionChain,
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

describe('collectDeletionChain', () => {
  it('returns just the target when nothing depends on it', () => {
    expect(collectDeletionChain(chain, 'c')).toEqual(['c'])
  })

  it('orders descendants before the target', () => {
    expect(collectDeletionChain(chain, 'a')).toEqual(['c', 'b', 'a'])
  })

  it('deletes a shared descendant before either of its parents', () => {
    // t -> a, t -> b, and both a and b -> d.
    const diamond = [
      node('t'),
      node('a', ['t']),
      node('b', ['t']),
      node('d', ['a', 'b']),
    ]
    const order = collectDeletionChain(diamond, 't')

    expect(order).toHaveLength(4)
    expect(order.at(-1)).toBe('t')
    // Every session precedes the ones it was built on.
    expect(order.indexOf('d')).toBeLessThan(order.indexOf('a'))
    expect(order.indexOf('d')).toBeLessThan(order.indexOf('b'))
    expect(order.indexOf('a')).toBeLessThan(order.indexOf('t'))
    expect(order.indexOf('b')).toBeLessThan(order.indexOf('t'))
  })

  it('lists each session once when reachable by several paths', () => {
    const diamond = [
      node('t'),
      node('a', ['t']),
      node('b', ['t']),
      node('d', ['a', 'b']),
    ]
    const order = collectDeletionChain(diamond, 't')
    expect(new Set(order).size).toBe(order.length)
  })

  it('ignores sessions on an unrelated branch', () => {
    const forked = [...chain, node('x'), node('y', ['x'])]
    expect(collectDeletionChain(forked, 'b')).toEqual(['c', 'b'])
  })

  it('returns nothing for an unknown target', () => {
    expect(collectDeletionChain(chain, 'nope')).toEqual([])
  })
})
