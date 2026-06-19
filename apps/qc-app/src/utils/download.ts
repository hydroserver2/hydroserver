/**
 * Browser-side delivery for export Blobs produced by the HydroServer client.
 *
 * The client (`@hydroserver/client`) is environment-agnostic: it fetches and
 * produces export data (e.g. `fetchCsvBlob`) but never decides how that data
 * reaches the user. Anchor-click download is a DOM-specific concern and
 * therefore lives here, in the consuming app.
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
