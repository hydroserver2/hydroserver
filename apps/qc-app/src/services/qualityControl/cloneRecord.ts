import { ObservationRecord } from '@uwrl/qc-utils'

export type CloneRecord = (record: ObservationRecord) => Promise<ObservationRecord>

/**
 * A standalone record holding a copy of `record`'s current window. The
 * observation store shares one record per datastream, so edits must happen
 * on a copy. `dataX`/`dataY` are views over a shared buffer, hence the copy.
 */
export const cloneRecord: CloneRecord = async (record) => {
  const copy = new ObservationRecord({
    datetimes: Float64Array.from(record.dataX),
    dataValues: Float32Array.from(record.dataY),
  })
  // The constructor starts loading without awaiting it.
  await copy.reload()
  return copy
}
