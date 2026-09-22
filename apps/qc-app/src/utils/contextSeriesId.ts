/**
 * Synthetic id for the grey source context drawn around the edit target. It
 * reads the source's own data, but needs an id of its own so the source can
 * also be plotted as an ordinary series beside it.
 */

export const CONTEXT_PREFIX = 'ctx:'

export function makeContextId(sourceId: string): string {
  return `${CONTEXT_PREFIX}${sourceId}`
}

export function isContextId(id: string | null | undefined): boolean {
  return !!id && id.startsWith(CONTEXT_PREFIX)
}
