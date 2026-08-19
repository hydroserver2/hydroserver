/**
 * Session dependency graph helpers.
 *
 * A session carries `dependencyIds` (the sessions it was built on), so its
 * edges point at ancestors. Deletion needs the opposite direction, which is
 * derived by inverting that list over the sessions already loaded.
 *
 * `dependencyIds` only rides along on the detail response, so callers must
 * list sessions with `expand_related: true`. Without it every session looks
 * like a leaf and the chain collapses to the target alone.
 */

/** The slice of a session this module needs, on either response shape. */
export interface SessionNode {
  id: string
  dependencyIds?: string[]
}

/** Maps a session id to the ids of the sessions built on top of it. */
export function buildDependentsMap(
  sessions: SessionNode[]
): Map<string, string[]> {
  const dependents = new Map<string, string[]>()
  for (const session of sessions) {
    for (const parentId of session.dependencyIds ?? []) {
      const existing = dependents.get(parentId)
      if (existing) existing.push(session.id)
      else dependents.set(parentId, [session.id])
    }
  }
  return dependents
}

/** True when another loaded session was built on top of this one. */
export function hasDependents(
  sessions: SessionNode[],
  sessionId: string
): boolean {
  return (buildDependentsMap(sessions).get(sessionId)?.length ?? 0) > 0
}

/**
 * The sessions that must be removed to delete `targetId`, ordered so each
 * one is free of dependents by the time its turn comes: descendants first,
 * target last. Empty when the target is not in `sessions`.
 */
export function collectDeletionChain(
  sessions: SessionNode[],
  targetId: string
): string[] {
  if (!sessions.some((s) => s.id === targetId)) return []

  const dependents = buildDependentsMap(sessions)
  const order: string[] = []
  const visited = new Set<string>()

  // Post-order over the dependents edges: a node is appended only after
  // everything reachable from it, which is exactly delete order.
  const visit = (id: string) => {
    if (visited.has(id)) return
    visited.add(id)
    for (const childId of dependents.get(id) ?? []) visit(childId)
    order.push(id)
  }
  visit(targetId)

  return order
}
