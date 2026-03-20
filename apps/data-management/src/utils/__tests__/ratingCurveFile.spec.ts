import { describe, expect, it } from 'vitest'
import {
  parseRatingCurveCsvFile,
  parseRatingCurveCsvText,
  toRatingCurveFileValidationMessage,
} from '@/utils/orchestration/ratingCurveFile'

describe('parseRatingCurveCsvText', () => {
  it('parses numeric rows with a header row', () => {
    const parsed = parseRatingCurveCsvText(
      'input_value,output_value\n0,0\n1.5,2.25\n'
    )

    expect(parsed.hasHeader).toBe(true)
    expect(parsed.rows).toEqual([
      { inputValue: 0, outputValue: 0 },
      { inputValue: 1.5, outputValue: 2.25 },
    ])
  })

  it('rejects non-numeric values in data rows', () => {
    expect(() =>
      parseRatingCurveCsvText('input_value,output_value\nabc,2\n')
    ).toThrow(/numeric input and output values/i)
  })

  it('rejects rows with more than two populated columns', () => {
    expect(() => parseRatingCurveCsvText('0,1,2\n')).toThrow(
      /exactly two columns/i
    )
  })

  it('parses quoted values and escaped quotes', () => {
    const parsed = parseRatingCurveCsvText('"0","1"\n"2","3"\n')
    expect(parsed.rows).toEqual([
      { inputValue: 0, outputValue: 1 },
      { inputValue: 2, outputValue: 3 },
    ])
  })

  it('rejects malformed quoted values', () => {
    expect(() => parseRatingCurveCsvText('"0,1\n')).toThrow(/unclosed quoted value/i)
  })

  it('rejects rows with fewer than two columns', () => {
    expect(() => parseRatingCurveCsvText('1\n')).toThrow(/exactly two columns/i)
  })

  it('accepts trailing empty columns and trims values', () => {
    const parsed = parseRatingCurveCsvText(' 1 , 2 ,\n')
    expect(parsed.rows).toEqual([{ inputValue: 1, outputValue: 2 }])
  })

  it('rejects CSV with only a header and no numeric data rows', () => {
    expect(() => parseRatingCurveCsvText('input,output\n')).toThrow(
      /at least one numeric row/i
    )
  })
})

describe('parseRatingCurveCsvFile', () => {
  it('parses file contents', async () => {
    const file = {
      text: async () => 'input,output\n1,2\n',
    } as File

    const parsed = await parseRatingCurveCsvFile(file)
    expect(parsed).toEqual({
      hasHeader: true,
      rows: [{ inputValue: 1, outputValue: 2 }],
    })
  })
})

describe('toRatingCurveFileValidationMessage', () => {
  it('returns the parser error message when present', () => {
    expect(toRatingCurveFileValidationMessage(new Error('bad data'))).toMatch(
      /bad data/
    )
  })

  it('falls back to default message for unknown errors', () => {
    expect(toRatingCurveFileValidationMessage(null)).toMatch(
      /two-column csv/i
    )
  })
})
