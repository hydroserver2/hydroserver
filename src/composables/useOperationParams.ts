/**
 * Per-datastream persistence for operation parameters (Find Gaps,
 * Fill Gaps). Parameters are keyed by datastream id so switching back
 * to a series restores the user's last-used threshold / cadence /
 * NoData value — otherwise every open resets to the datastream's
 * intended cadence and the user has to re-tune from scratch.
 *
 * Storage is a best-effort layer on top of localStorage: we swallow
 * serialisation errors and treat missing entries as "fall back to
 * defaults". Not appropriate for anything load-bearing, which is why
 * the store watcher still seeds defaults from the datastream when no
 * persisted value is available.
 */

const STORAGE_KEY = 'qc:opParams:v1'

export interface PersistedOpParams {
  gapAmount?: number
  gapUnit?: string
  fillAmount?: number
  fillUnit?: string
  noDataValue?: number
}

type AllPersisted = Record<string, PersistedOpParams>

function readAll(): AllPersisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? (parsed as AllPersisted) : {}
  } catch {
    return {}
  }
}

function writeAll(data: AllPersisted) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    /* quota exceeded, private browsing, etc. — swallow */
  }
}

export function loadOpParams(datastreamId: string | null | undefined): PersistedOpParams | null {
  if (!datastreamId) return null
  const all = readAll()
  return all[datastreamId] ?? null
}

export function saveOpParams(
  datastreamId: string | null | undefined,
  patch: PersistedOpParams
) {
  if (!datastreamId) return
  const all = readAll()
  all[datastreamId] = { ...all[datastreamId], ...patch }
  writeAll(all)
}
