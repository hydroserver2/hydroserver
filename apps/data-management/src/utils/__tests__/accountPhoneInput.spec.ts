import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, it } from 'vitest'
import { MaskInput } from 'maska'

const script = readFileSync(
  resolve(__dirname, '../../../../../django/static/js/phone-input.js'),
  'utf8'
)

async function mountPhone(value = '') {
  document.body.innerHTML =
    '<form><input type="tel" data-maska="(###) ###-####"></form>'
  const input = document.querySelector('input')!
  input.value = value
  new Function('Maska', script)({ MaskInput })
  await Promise.resolve()
  return input
}

function enter(
  input: HTMLInputElement,
  value: string,
  inputType = 'insertText'
) {
  input.value = value
  input.setSelectionRange(value.length, value.length)
  input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType }))
}

describe('account phone input matches v1', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('adds v1 punctuation while typing digits and validates completion', async () => {
    const input = await mountPhone()
    const expected = [
      '(8',
      '(80',
      '(801',
      '(801) 5',
      '(801) 55',
      '(801) 555',
      '(801) 555-1',
      '(801) 555-12',
      '(801) 555-123',
      '(801) 555-1234',
    ]
    for (const [index, digit] of [...'8015551234'].entries()) {
      enter(input, input.value + digit)
      expect(input.value).toBe(expected[index])
      expect(input.checkValidity()).toBe(index === 9)
    }
  })

  it('formats pasted numbers, filters letters, and limits input to ten digits', async () => {
    const input = await mountPhone()
    enter(input, 'abc801555123499', 'insertFromPaste')
    expect(input.value).toBe('(801) 555-1234')
    expect(input.checkValidity()).toBe(true)
  })

  it('formats existing values and submits the masked value like v1', async () => {
    const input = await mountPhone('8015551234')
    input.name = 'phone'
    expect(input.value).toBe('(801) 555-1234')
    expect(new FormData(input.form!).get('phone')).toBe('(801) 555-1234')
  })

  it('allows deleting across separators and clearing the optional field', async () => {
    const input = await mountPhone('(801) 555-1')
    enter(input, '(801) 555-', 'deleteContentBackward')
    expect(input.value).toBe('(801) 555-')
    enter(input, '(801) 555', 'deleteContentBackward')
    expect(input.value).toBe('(801) 555')
    enter(input, '', 'deleteContentBackward')
    expect(input.value).toBe('')
    expect(input.checkValidity()).toBe(true)
  })
})
