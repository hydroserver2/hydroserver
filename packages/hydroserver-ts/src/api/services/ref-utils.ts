// src/api/services/ref-utils.ts
export type WithId = { id: string }
export type ResourceRef<T extends WithId = WithId> = string | T | { id: string }

export function resolveId<T extends WithId>(
  ref?: ResourceRef<T>
): string | undefined {
  if (!ref) return undefined
  return typeof ref === 'string' ? ref : ref.id
}

/**
 * Convert ergonomic object/uuid refs into explicit *_Id string fields.
 * - mapping: { refKey: 'idKey', ... }   e.g. { workspace: 'workspaceId', thing: 'thingId' }
 * - Removes the original ref keys so they don’t leak into the query.
 */
export function coerceRefParams<
  P extends Record<string, any>,
  M extends Record<string, string>
>(
  params: P,
  mapping: M
): Omit<P, keyof M> & Partial<Record<M[keyof M], string>> {
  const out: Record<string, any> = { ...params }
  for (const [refKey, idKey] of Object.entries(mapping)) {
    const fromRef = resolveId(out[refKey])
    const fromId = out[idKey]
    if (fromRef !== undefined) out[idKey] = fromRef
    else if (typeof fromId === 'string') out[idKey] = fromId
    delete out[refKey]
  }
  return out as any
}

/* Common scoped param mixins you can reuse in ListParams */
export type WorkspaceScoped = {
  workspace?: ResourceRef
  workspaceId?: string
}

export type ThingScoped = {
  thing?: ResourceRef
  thingId?: string
}
