import type {
  Datastream,
  DatastreamExtended,
  QualityControlSession,
} from '@hydroserver/client'

const NUMBER = new Intl.NumberFormat()

/**
 * One-line recap of a datastream, so several derived from the same source
 * are distinguishable in a chooser: processing level, observation count,
 * and (when sessions are supplied) how many QC sessions it carries.
 */
export function datastreamSummary(
  datastream: Datastream & Partial<DatastreamExtended>,
  sessions?: QualityControlSession[]
): string {
  const parts: string[] = []
  const level =
    datastream.processingLevel?.definition || datastream.processingLevel?.code
  if (level) parts.push(`Level: ${level}`)
  parts.push(`${NUMBER.format(datastream.valueCount ?? 0)} obs`)
  if (sessions) {
    const inProgress = sessions.filter((s) => s.status === 'in_progress').length
    parts.push(
      `${sessions.length} session${sessions.length === 1 ? '' : 's'}${
        inProgress ? `, ${inProgress} in progress` : ''
      }`
    )
  }
  return parts.join(' · ')
}
