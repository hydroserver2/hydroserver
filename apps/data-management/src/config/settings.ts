import { AppSettings } from '@/models/settings'

let scriptTag: HTMLScriptElement | null;

if (import.meta.env.DEV) {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', 'http://127.0.0.1:8000', false);
  xhr.send(null);
  const indexHtml = xhr.status >= 200 && xhr.status < 300 ? xhr.responseText : null
  const parser = new DOMParser();
  const doc = indexHtml
    ? parser.parseFromString(indexHtml, 'text/html')
    : document.implementation.createHTMLDocument('');
  scriptTag = doc.getElementById('app-settings') as HTMLScriptElement;
} else {
  scriptTag = document.getElementById('app-settings') as HTMLScriptElement;
}

export const settings: AppSettings = JSON.parse(scriptTag.textContent || "{}");
