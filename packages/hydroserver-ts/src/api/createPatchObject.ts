/**
 * Creates an object that represents the differences (patches) between the
 * original and the updated objects.
 *
 * This function iterates through the properties of the updated object and compares each property
 * with the corresponding property in the original object. If a difference is found:
 * 1. For properties that are objects, it recursively computes the nested differences.
 * 2. For other properties, it directly assigns the updated value.
 *
 * Note: The function only checks properties that exist in the updated object.
 *
 * @param {any} original - The original object to compare from.
 * @param {any} updated - The updated object to compare against.
 * @returns {any} An object representing the differences between the two input objects.
 *                If two properties are identical, they won't appear in the result.
 */
export function createPatchObject(original: any, updated: any): any {
  const differences: any = {}
  for (let key in updated) {
    if (Array.isArray(updated[key])) {
      if (JSON.stringify(original[key]) !== JSON.stringify(updated[key])) {
        differences[key] = updated[key]
      }
    } else if (
      original[key] &&
      typeof original[key] === 'object' &&
      updated[key] &&
      typeof updated[key] === 'object'
    ) {
      const nestedDiff = createPatchObject(original[key], updated[key])
      if (Object.keys(nestedDiff).length > 0) {
        differences[key] = nestedDiff
      }
    } else if (JSON.stringify(original[key]) !== JSON.stringify(updated[key])) {
      differences[key] = updated[key]
    }
  }

  return differences
}
