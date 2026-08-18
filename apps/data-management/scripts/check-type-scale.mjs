#!/usr/bin/env node
/*
 * Enforces the data-management app's type system: the 5-step font-size
 * scale and font-weight/font-family tokens declared in the shared
 * packages/design-tokens CSS files.
 *
 * This is deliberately narrow. It only checks font-size, font-weight, and
 * font-family — not color, not spacing, not arbitrary px values. Widening
 * it to ban every raw literal in the codebase (colors, spacing, anything)
 * produces junk: a scan for "every hardcoded value" can't tell a deliberate
 * design decision from an incidental one, so the only way to pass is to
 * alias every value that already exists, which launders inconsistency
 * instead of fixing it. See git history around branch 511-design-system
 * for what that looked like — hundreds of `colors.hex1a2b3c`-style
 * indirections with no design payoff. Keep this file scoped to fonts.
 *
 * What's banned, and why each one bypasses the declared system:
 *   - A raw font-size/font-weight/font-family value in a <style> block
 *     (anything not `var(--hs-font-*)`, `var(--hs-font-weight-*)`, or
 *     `inherit`).
 *   - Tailwind's own type scale in a class attribute: `text-xs` / `text-sm`
 *     / `text-base` / `text-lg` / `text-xl` / `text-2xl` etc., and its
 *     arbitrary-value escape hatch `text-[13px]` / `text-[0.8rem]` (unless
 *     the bracket itself references an --hs-font-* token, e.g.
 *     `text-[length:var(--hs-font-sm)]` — that's just how you reach a
 *     token from inside a Tailwind arbitrary-selector like `[&_x]:...`).
 *   - Tailwind's own weight scale: `font-medium`, `font-semibold`,
 *     `font-bold`, etc. Use Vuetify's own (already-loaded, already free)
 *     `.font-weight-regular/medium/semibold/bold` classes instead, so
 *     weight has exactly one spelling app-wide, not two.
 *   - An inline `style="font-size: 13px"` / `:style="{ fontWeight: 600 }"`.
 *   - A `var(--hs-font-*)` reference that doesn't match any token actually
 *     declared in tokens.css/fonts.css (catches typos and drift).
 *
 * If a legitimate case doesn't fit the five sizes or four weights, that's
 * a signal the content needs a rethink — not a reason to add a sixth
 * token or to reach past this script.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = path.resolve(appRoot, '../..')
const sourceRoot = path.join(appRoot, 'src')
const sourceExtensions = new Set(['.vue', '.scss', '.css', '.ts'])

function collectFiles(root, extensions) {
  return fs.readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(root, entry.name)
    if (entry.isDirectory()) return collectFiles(entryPath, extensions)
    return extensions.has(path.extname(entry.name)) ? [entryPath] : []
  })
}

// --- Build the token allow-list from the source of truth, rather than
// hardcoding it here, so this script can't silently drift from the real
// scale.
const tokenSourceFiles = [
  path.join(repoRoot, 'packages/design-tokens/fonts.css'),
  path.join(repoRoot, 'packages/design-tokens/tokens.css'),
]
const declaredFontVars = new Set()
for (const file of tokenSourceFiles) {
  if (!fs.existsSync(file)) continue
  const source = fs.readFileSync(file, 'utf8')
  for (const match of source.matchAll(/(--hs-font(?:-[\w]+)*)\s*:/g)) {
    declaredFontVars.add(match[1])
  }
}
const sizeVars = [...declaredFontVars].filter(
  (name) => !name.startsWith('--hs-font-weight-') && name !== '--hs-font-body' && name !== '--hs-font-data'
)
const weightVars = [...declaredFontVars].filter((name) => name.startsWith('--hs-font-weight-'))

if (sizeVars.length === 0 || weightVars.length === 0) {
  console.error(
    'check-type-scale: could not find any --hs-font-* size or weight tokens in ' +
      tokenSourceFiles.join(', ') +
      ' — did the token files move?'
  )
  process.exit(1)
}

const files = collectFiles(sourceRoot, sourceExtensions)
const violations = []

function report(file, source, index, message) {
  const line = source.slice(0, index).split('\n').length
  violations.push(`${path.relative(repoRoot, file)}:${line}  ${message}`)
}

const TAILWIND_SIZE_CLASSES = new Set([
  'text-xs',
  'text-sm',
  'text-base',
  'text-lg',
  'text-xl',
  'text-2xl',
  'text-3xl',
  'text-4xl',
  'text-5xl',
  'text-6xl',
  'text-7xl',
  'text-8xl',
  'text-9xl',
])
const TAILWIND_WEIGHT_CLASSES = new Set([
  'font-thin',
  'font-extralight',
  'font-light',
  'font-normal',
  'font-medium',
  'font-semibold',
  'font-bold',
  'font-extrabold',
  'font-black',
])

for (const file of files) {
  const source = fs.readFileSync(file, 'utf8')

  // 1) Raw font-size / font-weight / font-family in CSS. The negative
  // lookbehind keeps this from matching inside a longer identifier like a
  // Sass variable ($tooltip-font-size) or a BEM class
  // (.foo__font-size-label) — only the actual CSS property counts.
  for (const match of source.matchAll(/(?<![\w$-])font-size\s*:\s*([^;]+);/g)) {
    const value = match[1].trim()
    if (!/^var\(--hs-font-[\w-]+\)$/.test(value) && value !== 'inherit') {
      report(
        file,
        source,
        match.index,
        `raw font-size "${value}" — use one of the .hs-text-* classes or a var(--hs-font-*) token from the type scale`
      )
    }
  }
  for (const match of source.matchAll(/(?<![\w$-])font-weight\s*:\s*([^;]+);/g)) {
    const value = match[1].trim()
    if (!/^var\(--hs-font-weight-[\w-]+\)$/.test(value) && value !== 'inherit') {
      report(
        file,
        source,
        match.index,
        `raw font-weight "${value}" — use Vuetify's .font-weight-regular/medium/semibold/bold class, or var(--hs-font-weight-*) if this rule has no template element to hang a class on`
      )
    }
  }
  for (const match of source.matchAll(/(?<![\w$-])font-family\s*:\s*([^;]+);/g)) {
    const value = match[1].trim()
    if (!/^var\(--hs-font-(display|body|data)\)$/.test(value) && value !== 'inherit') {
      report(
        file,
        source,
        match.index,
        `raw font-family "${value}" — use var(--hs-font-body|data) (or the .hs-font-data class)`
      )
    }
  }

  // 2) Tailwind's arbitrary-value font-size escape hatch, e.g. text-[13px],
  // text-[0.8rem] — but not text-[length:var(--hs-font-sm)], which is a
  // legitimate way to reach a token from inside a Tailwind selector.
  for (const match of source.matchAll(/text-\[([^\]]+)\]/g)) {
    const inner = match[1]
    const looksLikeFontSize = /^(length:)?-?[\d.]+(px|rem|em)$/.test(inner)
    if (looksLikeFontSize) {
      report(
        file,
        source,
        match.index,
        `Tailwind arbitrary font-size "text-[${inner}]" — use an hs-text-* class instead`
      )
    }
  }

  // 3) Tailwind's own named type scale / weight scale in class attributes.
  // Vue's shorthand template syntax means "class" can appear as a static
  // attribute, inside a :class="[...]" array, or as a key in a
  // :class="{...}" binding object — check individual tokens, not
  // substrings, so this doesn't false-positive on hs-text-sm etc.
  for (const match of source.matchAll(/\bclass(?:Name)?\s*=\s*"([^"]*)"/g)) {
    const classList = match[1].split(/\s+/)
    for (const token of classList) {
      if (TAILWIND_SIZE_CLASSES.has(token)) {
        report(
          file,
          source,
          match.index,
          `Tailwind type-scale class "${token}" — use the matching hs-text-* class from the app's own type scale instead`
        )
      }
      if (TAILWIND_WEIGHT_CLASSES.has(token)) {
        report(
          file,
          source,
          match.index,
          `Tailwind weight class "${token}" — use Vuetify's .font-weight-regular/medium/semibold/bold instead, so weight has one spelling app-wide`
        )
      }
    }
  }
  // `:class="{ 'text-sm': someCondition }"` / `:class="['text-sm', ...]"` —
  // catch quoted class tokens the same way, wherever they appear as object
  // keys or array entries in a class binding.
  for (const match of source.matchAll(/:class(?:Name)?\s*=\s*"[^"]*"/g)) {
    const binding = match[0]
    for (const tokenMatch of binding.matchAll(/['"]([\w-]+)['"]/g)) {
      const token = tokenMatch[1]
      if (TAILWIND_SIZE_CLASSES.has(token) || TAILWIND_WEIGHT_CLASSES.has(token)) {
        report(
          file,
          source,
          match.index,
          `Tailwind class "${token}" inside a :class binding — use the app's hs-text-*/font-weight-* classes instead`
        )
      }
    }
  }

  // 4) Inline style bindings that set a raw font value directly, e.g.
  // style="font-size: 13px" or :style="{ fontSize: '13px', fontWeight: 600 }".
  for (const match of source.matchAll(/fontSize\s*:\s*['"]?([\w.%-]+)/g)) {
    report(
      file,
      source,
      match.index,
      `inline fontSize "${match[1]}" in a :style binding — use an hs-text-* class instead`
    )
  }
  for (const match of source.matchAll(/fontWeight\s*:\s*['"]?([\w-]+)/g)) {
    report(
      file,
      source,
      match.index,
      `inline fontWeight "${match[1]}" in a :style binding — use a font-weight-* class instead`
    )
  }

  // 5) Catch typos/drift: a var(--hs-font-*) reference that isn't actually
  // declared anywhere.
  for (const match of source.matchAll(/var\((--hs-font(?:-[\w-]+)?)\)/g)) {
    if (!declaredFontVars.has(match[1])) {
      report(
        file,
        source,
        match.index,
        `undefined type token ${match[1]} — not declared in tokens.css or fonts.css (typo?)`
      )
    }
  }
}

if (violations.length) {
  console.error(
    `Type-scale conformance failed (${violations.length} violation${violations.length === 1 ? '' : 's'}):\n`
  )
  console.error(violations.join('\n'))
  console.error(
    `\nSize scale: ${sizeVars.join(', ')}\nWeight scale: ${weightVars.join(', ')}\nSee packages/design-tokens/tokens.css for what each size means.`
  )
  process.exit(1)
}

console.log(`Type-scale conformance passed (${files.length} source files checked).`)
