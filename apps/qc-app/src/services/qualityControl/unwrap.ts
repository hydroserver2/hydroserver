import type { ApiResponse } from '@hydroserver/client'

/**
 * Unwrap a HydroServer `ApiResponse`, returning its data or throwing the
 * server message. The QC service methods (like the rest of the SDK) never
 * throw on HTTP errors; the session orchestration wants a thrown error it can
 * surface, so this bridges the two.
 */
export function unwrap<T>(res: ApiResponse<T>): T {
  if (!res.ok) throw new Error(res.message || 'QC API request failed.')
  return res.data
}
