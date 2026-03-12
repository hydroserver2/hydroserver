export type RatingCurveCsvRow = {
  inputValue: number
  outputValue: number
}

export type ParsedRatingCurveCsv = {
  rows: RatingCurveCsvRow[]
  hasHeader: boolean
}

function parseCsvLine(line: string): string[] {
  const columns: string[] = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]

    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i += 1
        continue
      }
      inQuotes = !inQuotes
      continue
    }

    if (char === ',' && !inQuotes) {
      columns.push(current)
      current = ''
      continue
    }

    current += char
  }

  if (inQuotes) {
    throw new Error('contains an unclosed quoted value')
  }

  columns.push(current)
  return columns
}

function parseFiniteNumber(value: string): number | null {
  const normalized = value.trim()
  if (!normalized) return null
  const parsed = Number(normalized)
  if (!Number.isFinite(parsed)) return null
  return parsed
}

function extractTwoColumns(columns: string[]): [string, string] {
  if (columns.length < 2) {
    throw new Error('must contain exactly two columns')
  }

  if (columns.length > 2) {
    const hasNonEmptyExtraColumn = columns
      .slice(2)
      .some((column) => column.trim().length > 0)
    if (hasNonEmptyExtraColumn) {
      throw new Error('must contain exactly two columns')
    }
  }

  return [columns[0].trim(), columns[1].trim()]
}

export function parseRatingCurveCsvText(text: string): ParsedRatingCurveCsv {
  const normalizedText = text.replace(/^\uFEFF/, '')
  const lines = normalizedText.split(/\r?\n/)

  const rows: RatingCurveCsvRow[] = []
  let sawHeader = false
  let sawDataRow = false

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index]
    if (!rawLine.trim()) continue

    let columns: string[]
    try {
      columns = parseCsvLine(rawLine)
    } catch (error: any) {
      throw new Error(`Line ${index + 1} ${error?.message || 'is invalid'}.`)
    }

    let inputRaw = ''
    let outputRaw = ''
    try {
      ;[inputRaw, outputRaw] = extractTwoColumns(columns)
    } catch (error: any) {
      throw new Error(`Line ${index + 1} ${error?.message || 'is invalid'}.`)
    }

    const inputValue = parseFiniteNumber(inputRaw)
    const outputValue = parseFiniteNumber(outputRaw)

    const canTreatAsHeader =
      !sawHeader &&
      !sawDataRow &&
      inputValue === null &&
      outputValue === null

    if (canTreatAsHeader) {
      sawHeader = true
      continue
    }

    if (inputValue === null || outputValue === null) {
      throw new Error(
        `Line ${index + 1} must contain numeric input and output values.`
      )
    }

    rows.push({ inputValue, outputValue })
    sawDataRow = true
  }

  if (!rows.length) {
    throw new Error(
      'CSV must include at least one numeric row with input and output values.'
    )
  }

  return { rows, hasHeader: sawHeader }
}

export async function parseRatingCurveCsvFile(
  file: File
): Promise<ParsedRatingCurveCsv> {
  const text = await file.text()
  return parseRatingCurveCsvText(text)
}

export function toRatingCurveFileValidationMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return `Invalid rating curve CSV: ${error.message}`
  }
  return 'Invalid rating curve CSV. Use a two-column CSV with numeric input and output values.'
}
