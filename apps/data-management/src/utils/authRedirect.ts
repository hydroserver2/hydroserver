const DEFAULT_POST_LOGIN_PATH = '/sites'
const LOGIN_PATH = '/login'

type RedirectQueryValue = string | null | (string | null)[] | undefined

export function getSafePostLoginPath(
  value: RedirectQueryValue
): string | null {
  const next = Array.isArray(value) ? value[0] : value
  if (!next) return null

  let path: string
  if (next.startsWith('/') && !next.startsWith('//')) {
    path = next
  } else {
    try {
      const url = new URL(next, window.location.origin)
      if (url.origin !== window.location.origin) return null
      path = `${url.pathname}${url.search}${url.hash}`
    } catch {
      return null
    }
  }

  if (path === LOGIN_PATH || path.startsWith(`${LOGIN_PATH}?`)) return null
  return path
}

export function getPostLoginPath(value: RedirectQueryValue): string {
  return getSafePostLoginPath(value) || DEFAULT_POST_LOGIN_PATH
}

export function requiresHardNavigation(path: string): boolean {
  return path === '/qc' || path.startsWith('/qc/')
}
