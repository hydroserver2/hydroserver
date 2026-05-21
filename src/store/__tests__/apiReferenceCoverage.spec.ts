import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const STORE_DIR = path.resolve(__dirname, '..')
const API_REF = path.resolve(__dirname, '..', '..', '..', 'docs', 'API_REFERENCE.md')

/**
 * Parses the identifiers a store exposes by reading the file's
 * `return { ... }` block at the bottom of the defineStore setup
 * function. Commented-out lines are skipped. Trailing inline comments
 * after an identifier are stripped.
 *
 * Returns null when the file isn't a defineStore call (e.g. index.ts).
 */
function parseStoreExports(source: string): string[] | null {
  if (!/\bdefineStore\b/.test(source)) return null

  const lines = source.split(/\r?\n/)
  // Find the LAST `  return {` line — defineStore setup functions can
  // have inner `return {` (e.g. inside helpers); the outer one is the
  // store's exported shape and always at indent 2.
  let start = -1
  for (let i = lines.length - 1; i >= 0; i--) {
    if (/^\s{0,2}return \{\s*$/.test(lines[i]!)) {
      start = i
      break
    }
  }
  if (start < 0) return null

  const exports: string[] = []
  for (let i = start + 1; i < lines.length; i++) {
    const raw = lines[i]!
    if (/^\s*\}/.test(raw)) break
    // Strip trailing comment + trailing comma + whitespace.
    const stripped = raw.replace(/\/\/.*$/, '').trim().replace(/,$/, '').trim()
    if (!stripped) continue
    // Skip lines that don't look like a bare identifier (e.g.
    // commented-out `// foo,` lines that the regex above didn't touch
    // because the slash-slash sat at the start).
    if (!/^[a-zA-Z_]\w*$/.test(stripped)) continue
    exports.push(stripped)
  }
  return exports
}

function readApiReference(): string {
  return readFileSync(API_REF, 'utf8')
}

/**
 * Every store file that defines a Pinia store. `index.ts` is the
 * pinia plugin wiring; not a store itself.
 */
function listStoreFiles(): string[] {
  return readdirSync(STORE_DIR, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith('.ts') && e.name !== 'index.ts')
    .map((e) => path.join(STORE_DIR, e.name))
}

describe('API_REFERENCE.md Pinia store coverage', () => {
  const refText = readApiReference()
  const storeFiles = listStoreFiles()

  for (const filePath of storeFiles) {
    const source = readFileSync(filePath, 'utf8')
    const exports = parseStoreExports(source)
    if (!exports) continue
    const fileName = path.basename(filePath)

    describe(fileName, () => {
      for (const name of exports) {
        it(`documents \`${name}\` in docs/API_REFERENCE.md`, () => {
          // Loose substring check: we only want to know the name is
          // mentioned somewhere in the doc. Don't enforce backtick
          // wrapping or table-cell shape so legitimate prose mentions
          // pass too.
          expect(refText).toContain(name)
        })
      }
    })
  }
})
