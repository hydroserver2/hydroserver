function handler(event) {
  var request = event.request;
  var uri = request.uri;
  // If the URI ends with a slash or doesn't have a dot, return the main index.html
  if (uri.endsWith("/") || !uri.includes(".")) {
    request.uri = "/index.html";
  }
  return request;
}