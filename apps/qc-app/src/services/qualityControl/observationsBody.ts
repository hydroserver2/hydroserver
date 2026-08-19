/** Bulk observations body for the replace-mode createObservations endpoint. */
export interface ObservationBulkPostBody {
  fields: ('phenomenonTime' | 'result')[]
  data: unknown[][]
}

/**
 * Serialize a record's (dataX, dataY) into a replace-mode bulk observations
 * body: epoch-ms timestamps become ISO strings paired with their results.
 * (Qualifier serialization is still pending in the data layer.)
 */
export function observationsBulkBody(record: {
  dataX: ArrayLike<number>
  dataY: ArrayLike<number>
}): ObservationBulkPostBody {
  const ys = record.dataY
  return {
    fields: ['phenomenonTime', 'result'],
    data: Array.from(record.dataX).map((ts, i) => [
      new Date(ts).toISOString(),
      ys[i],
    ]),
  }
}
