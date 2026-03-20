import { createPatchObject } from '../createPatchObject'
import { describe, it, expect } from 'vitest'

describe('createPatchObject', () => {
  it('should return an empty object for identical inputs', () => {
    const original = { name: 'Alice', age: 25 }
    const updated = { name: 'Alice', age: 25 }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({})
  })

  it('should return full updated object for non-existing original', () => {
    const original = {}
    const updated = { name: 'Bob' }

    const result = createPatchObject(original, updated)

    expect(result).toEqual(updated)
  })

  it('should return differences for flat objects', () => {
    const original = { name: 'Alice', age: 25 }
    const updated = { name: 'Alice', age: 26 }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({ age: 26 })
  })

  it('should return differences for nested objects', () => {
    const original = {
      name: 'Alice',
      address: { city: 'NYC', zip: '10001' },
    }
    const updated = {
      name: 'Alice',
      address: { city: 'LA', zip: '10001' },
    }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({
      address: { city: 'LA' },
    })
  })

  it('should handle null values correctly', () => {
    const original = { name: 'Alice', age: null }
    const updated = { name: 'Alice', age: 26 }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({ age: 26 })
  })
})

describe('createPatchObject for nested objects', () => {
  it('should detect changes in top-level properties', () => {
    const original = {
      id: '1',
      email: 'original@test.com',
    }

    const updated = {
      id: '1',
      email: 'updated@test.com',
    }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({ email: 'updated@test.com' })
  })

  it('should detect nested changes in organization property', () => {
    const original = {
      id: '1',
      email: 'original@test.com',
      organization: {
        name: 'OriginalOrg',
        code: '001',
      },
    }

    const updated = {
      id: '1',
      email: 'original@test.com',
      organization: {
        name: 'UpdatedOrg',
        code: '001',
      },
    }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({ organization: { name: 'UpdatedOrg' } })
  })

  it('should handle null values in nested objects', () => {
    const original = {
      id: '1',
      email: 'original@test.com',
      organization: {
        name: 'OriginalOrg',
        code: '001',
      },
    }

    const updated = {
      id: '1',
      email: 'original@test.com',
      organization: null,
    }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({ organization: null })
  })

  it('should handle arrays correctly', () => {
    const original = { names: ['Alice', 'Bob'] }
    const updated = { names: ['Alice', 'Bob', 'Charlie'] }

    const result = createPatchObject(original, updated)

    expect(result).toEqual({
      names: ['Alice', 'Bob', 'Charlie'],
    })
  })
})
