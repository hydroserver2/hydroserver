// Plotly mutates the graph div throughout an asynchronous draw. Starting a
// second draw on it before the first settles can restore stale traces/ranges
// and lose WebGL contexts. Keep each graph's draws in request order.
const pendingDraws = new WeakMap<HTMLElement, Promise<void>>()

export function queuePlotDraw(
  target: HTMLElement,
  draw: () => Promise<void>
): Promise<void> {
  const previous = pendingDraws.get(target)
  const next = previous ? previous.catch(() => undefined).then(draw) : draw()
  pendingDraws.set(target, next)
  const settled = () => {
    if (pendingDraws.get(target) === next) pendingDraws.delete(target)
  }
  void next.then(settled, settled)
  return next
}
