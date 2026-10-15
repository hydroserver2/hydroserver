import type { RouteLocationRaw } from 'vue-router'

/** Where to go after the workspace picker: `next` is a route name or a path. */
export function nextLocation(next: unknown): RouteLocationRaw {
  const target = typeof next === 'string' && next ? next : 'Home'
  return target.startsWith('/') ? { path: target } : { name: target }
}
