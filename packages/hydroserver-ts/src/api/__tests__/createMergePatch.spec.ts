import { describe, expect, it } from 'vitest'
import cases from '../../../../../django/contracts/merge-patch-cases.json'
import { createMergePatch } from '../createMergePatch'

describe('createMergePatch', () => {
  it.each(cases)('$name', ({ original, updated, patch }) => {
    const originalBefore = JSON.stringify(original)
    const updatedBefore = JSON.stringify(updated)

    expect(createMergePatch(original, updated)).toEqual(patch)
    expect(JSON.stringify(original)).toBe(originalBefore)
    expect(JSON.stringify(updated)).toBe(updatedBefore)
  })

  it('preserves omitted top-level fields in partial resource updates', () => {
    expect(
      createMergePatch(
        { name: 'Task', description: 'Keep me' },
        { name: 'Renamed' }
      )
    ).toEqual({ name: 'Renamed' })
  })

  it('preserves explicit deletion markers and omits undefined fields', () => {
    expect(
      createMergePatch(
        { description: 'Remove me', name: 'Keep me' },
        {
          description: null,
          name: undefined,
        }
      )
    ).toEqual({ description: null })
  })

  it('deletes nested keys set to undefined', () => {
    expect(
      createMergePatch(
        { taskVariables: { station: 'A', parameter: 'temperature' } },
        { taskVariables: { station: 'A', parameter: undefined } }
      )
    ).toEqual({ taskVariables: { parameter: null } })
  })

  it('compares dates as serialized values', () => {
    expect(
      createMergePatch(
        { startTime: new Date('2026-01-01') },
        { startTime: new Date('2026-02-01') }
      )
    ).toEqual({ startTime: new Date('2026-02-01') })
  })

  it('handles dictionary keys named __proto__ without modifying prototypes', () => {
    const updated = JSON.parse(
      '{"taskVariables":{"__proto__":{"station":"A"}}}'
    )
    const patch = createMergePatch({ taskVariables: {} }, updated)
    expect(JSON.stringify(patch)).toBe(JSON.stringify(updated))
    expect(Object.getPrototypeOf(patch.taskVariables)).toBe(Object.prototype)
  })

  it.each(['constructor', 'toString', '__proto__'])(
    'adds an empty object under the own property %s',
    (key) => {
      const updated = { taskVariables: { [key]: {} } }
      const patch = createMergePatch({ taskVariables: {} }, updated)

      expect(JSON.stringify(patch)).toBe(JSON.stringify(updated))
      expect(Object.hasOwn(patch.taskVariables as object, key)).toBe(true)
      expect(Object.getPrototypeOf(patch.taskVariables)).toBe(Object.prototype)
    }
  )

  it.each(['constructor', 'toString', '__proto__'])(
    'deletes the own property %s when omitted from the updated object',
    (key) => {
      const original = { taskVariables: { [key]: 'A', parameter: 'temperature' } }
      const updated = { taskVariables: { parameter: 'temperature' } }

      expect(createMergePatch(original, updated)).toEqual({
        taskVariables: { [key]: null },
      })
    }
  )
})
