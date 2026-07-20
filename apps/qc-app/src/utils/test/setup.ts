// jsdom doesn't implement HTMLCanvasElement.prototype.getContext, and
// Vuetify's measurement pass calls it during component mount, spamming
// "Not implemented" warnings into the test output. Stub with a no-op
// 2D context so the call returns something benign.
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = (() => null) as any
}
