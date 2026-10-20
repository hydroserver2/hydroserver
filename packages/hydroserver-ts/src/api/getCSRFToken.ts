let csrfCookieName = 'csrftoken'

export function registerCSRFCookieName(name: string) {
  csrfCookieName = name
}

export function getCSRFToken(): string | null {
  if (typeof document === 'undefined') return null

  const name = `${csrfCookieName}=`
  const decodedCookies = decodeURIComponent(document.cookie || '')
  const parts = decodedCookies.split(';')
  for (const part of parts) {
    const c = part.trim()
    if (c.startsWith(name)) {
      return c.substring(name.length)
    }
  }
  return null
}
