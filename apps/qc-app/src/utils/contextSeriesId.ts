/**
 * Synthetic id for a context series: a datastream drawn from its own server
 * data beside the edit target. The edit target's source is drawn this way
 * around the session window, and so is the edit target itself when it is
 * also plotted, so each can sit beside an ordinary series of the same
 * datastream.
 */

export const CONTEXT_PREFIX = 'ctx:'

export function makeContextId(datastreamId: string): string {
  return `${CONTEXT_PREFIX}${datastreamId}`
}

export function isContextId(id: string | null | undefined): boolean {
  return !!id && id.startsWith(CONTEXT_PREFIX)
}

/** The datastream a series id draws: the id itself, or a context id's datastream. */
export function contextTargetId(id: string): string {
  return isContextId(id) ? id.slice(CONTEXT_PREFIX.length) : id
}
