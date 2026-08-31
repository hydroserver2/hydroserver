// Fetches the backend settings from Django and adds them to
// dist/index.html's #app-settings tag.

import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const distIndexPath = path.join(here, '..', '..', 'dist', 'index.html')

const apiBaseUrl = process.env.E2E_API_BASE_URL
if (!apiBaseUrl) {
  throw new Error(
    'E2E_API_BASE_URL is required to inject live settings into the built e2e bundle'
  )
}

async function fetchSettingsHtml(retries = 120, delayMs = 1000) {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const res = await fetch(apiBaseUrl + '/')
      if (res.ok) return await res.text()
    } catch {
      // Django may not have finished starting yet; keep retrying.
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs))
  }
  throw new Error(`Timed out waiting for ${apiBaseUrl}/ to become available`)
}

const html = await fetchSettingsHtml()
const match = html.match(
  /<script id="app-settings" type="application\/json">([\s\S]*?)<\/script>/
)
if (!match) {
  throw new Error(
    `Could not find a #app-settings script tag in the response from ${apiBaseUrl}/`
  )
}
const settingsJson = match[1]

const distHtml = await readFile(distIndexPath, 'utf-8')
const injected = distHtml.replace(
  '<script id="app-settings" type="application/json"></script>',
  `<script id="app-settings" type="application/json">${settingsJson}</script>`
)
if (injected === distHtml) {
  throw new Error(
    `Could not find the empty #app-settings tag to replace in ${distIndexPath}`
  )
}

await writeFile(distIndexPath, injected, 'utf-8')
console.log('Injected live backend settings into dist/index.html for the e2e preview server.')
