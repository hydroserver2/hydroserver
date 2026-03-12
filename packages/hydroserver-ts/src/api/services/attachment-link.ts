type LinkLike = {
  link?: unknown
}

function pathShouldUseApiOrigin(pathname: string) {
  return pathname.startsWith('/media/') || pathname.startsWith('/api/data/')
}

export function preferredApiOrigin(host?: string | null) {
  try {
    if (host) {
      return new URL(host, globalThis.location?.origin).origin
    }
  } catch {
    // no-op
  }

  try {
    return globalThis.location?.origin ?? null
  } catch {
    return null
  }
}

export function normalizeAttachmentLink(
  link: string,
  host?: string | null
): string {
  const preferredOrigin = preferredApiOrigin(host)
  if (!preferredOrigin) return link

  try {
    const parsed = new URL(link, preferredOrigin)
    if (
      parsed.origin !== preferredOrigin &&
      pathShouldUseApiOrigin(parsed.pathname)
    ) {
      return new URL(
        `${parsed.pathname}${parsed.search}${parsed.hash}`,
        preferredOrigin
      ).toString()
    }
    return parsed.toString()
  } catch {
    return link
  }
}

export function normalizeAttachmentRecord<T extends LinkLike>(
  value: T,
  host?: string | null
): T {
  if (!value || typeof value !== 'object' || typeof value.link !== 'string') {
    return value
  }

  return {
    ...value,
    link: normalizeAttachmentLink(value.link, host),
  }
}

export function normalizeAttachmentCollection<T extends LinkLike>(
  data: T[] | T | null | undefined,
  host?: string | null
): T[] | T | null | undefined {
  if (Array.isArray(data)) {
    return data.map((item) => normalizeAttachmentRecord(item, host))
  }
  if (data && typeof data === 'object') {
    return normalizeAttachmentRecord(data, host)
  }
  return data
}
