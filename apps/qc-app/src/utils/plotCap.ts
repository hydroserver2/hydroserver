/** Datastreams the user can plot at once. One more slot is kept for the
 *  datastream being edited. */
export const PLOT_CAP = 4

/** History snapshots shown at once. Each is a full copy of the session's
 *  data, so a few on a large datastream can exhaust the tab's memory. */
export const SNAPSHOT_CAP = 2

/** The warning for datastreams left off the plot by `PLOT_CAP`. */
export function plotCapMessage(leftOff: string[]): string {
  const names =
    leftOff.length < 2
      ? leftOff.join('')
      : `${leftOff.slice(0, -1).join(', ')} and ${leftOff[leftOff.length - 1]}`
  const verb = leftOff.length === 1 ? 'was' : 'were'
  return `Up to ${PLOT_CAP} datastreams can be plotted at once, so ${names} ${verb} left off.`
}
