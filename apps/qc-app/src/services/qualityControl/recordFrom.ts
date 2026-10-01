import { ObservationRecord } from '@uwrl/qc-utils'

/**
 * A standalone record over copies of `datetimes` and `dataValues`. The
 * observation store shares one record per datastream, so edits must happen
 * on a record of their own.
 */
export async function recordFrom(
  datetimes: ArrayLike<number>,
  dataValues: ArrayLike<number>
): Promise<ObservationRecord> {
  const record = new ObservationRecord({
    datetimes: Float64Array.from(datetimes),
    dataValues: Float32Array.from(dataValues),
  })
  // The constructor starts loading without awaiting it.
  await record.reload()
  return record
}
