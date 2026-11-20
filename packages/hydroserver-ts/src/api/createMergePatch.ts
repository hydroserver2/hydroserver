const isObject = (value: unknown): value is Record<string, unknown> =>
  value !== null &&
  typeof value === 'object' &&
  !Array.isArray(value) &&
  !(value instanceof Date)

/**
 * Build a JSON Merge Patch for supplied resource fields. Top-level omissions
 * leave fields untouched; removed or undefined keys within supplied objects
 * become null.
 * Arrays are replaced in full. Inputs are never modified.
 */
export function createMergePatch(
  original: Record<string, unknown>,
  updated: Record<string, unknown>,
  removeMissing = false
): Record<string, unknown> {
  const entries: [string, unknown][] = []

  for (const [key, value] of Object.entries(updated)) {
    if (value === undefined) continue
    const previous = Object.hasOwn(original, key) ? original[key] : undefined
    if (isObject(value)) {
      const previousIsObject = isObject(previous)
      const nested = createMergePatch(
        previousIsObject ? previous : {},
        value,
        true
      )
      if (!previousIsObject || Object.keys(nested).length > 0) {
        entries.push([key, nested])
      }
    } else if (JSON.stringify(previous) !== JSON.stringify(value)) {
      entries.push([key, value])
    }
  }

  if (removeMissing) {
    // Inside objects, a key set to undefined counts as removed, like a deleted key.
    for (const key of Object.keys(original)) {
      if (!Object.hasOwn(updated, key) || updated[key] === undefined) {
        entries.push([key, null])
      }
    }
  }

  return Object.fromEntries(entries)
}
