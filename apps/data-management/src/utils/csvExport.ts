import hs from '@hydroserver/client'
import JSZip from 'jszip'
import { downloadBlob } from '@/utils/download'

/**
 * App-side CSV export delivery.
 *
 * The client exposes a single data-only primitive — `fetchCsvBlob` — that
 * follows the Result model and never touches the DOM. Everything
 * environment-specific lives here: batching, ZIP bundling, and the browser
 * anchor-click download. These helpers throw on failure so existing try/catch
 * call sites keep working.
 */
export async function downloadDatastreamCsv(id: string, filename?: string) {
  const res = await hs.datastreams.fetchCsvBlob(id)
  if (!res.ok) {
    throw new Error(res.message || 'Failed to fetch datastream CSV.')
  }
  const blob =
    res.data instanceof Blob
      ? res.data
      : new Blob([res.data as any], { type: 'text/csv' })
  downloadBlob(blob, filename ?? `datastream_${id}.csv`)
}

/**
 * Fetch many datastream CSVs (bounded concurrency), bundle them into a single
 * ZIP, and trigger a browser download.
 */
export async function downloadDatastreamsCsvZip(
  datastreams: Array<string | { id: string }>,
  zipName = 'datastreams.zip'
) {
  const ids = datastreams.map((ds) => (typeof ds === 'string' ? ds : ds.id))

  const CONCURRENCY = 5
  const blobs: Array<{ id: string; blob: Blob }> = []
  for (let i = 0; i < ids.length; i += CONCURRENCY) {
    const chunk = ids.slice(i, i + CONCURRENCY)
    const chunkResults = await Promise.all(
      chunk.map(async (id) => {
        const res = await hs.datastreams.fetchCsvBlob(id)
        if (!res.ok) {
          throw new Error(
            res.message || `Failed to fetch CSV for datastream ${id}.`
          )
        }
        const blob =
          res.data instanceof Blob
            ? res.data
            : new Blob([res.data as any], { type: 'text/csv' })
        return { id, blob }
      })
    )
    blobs.push(...chunkResults)
  }

  const zip = new JSZip()
  for (const { id, blob } of blobs) {
    zip.file(`datastream_${id}.csv`, blob)
  }

  const archive = await zip.generateAsync({ type: 'blob' })
  downloadBlob(archive, zipName)
}
