/**
 * Flow helpers shared by every mocked e2e spec.
 *
 * Specs should usually go through these so the "boot → pick workspace
 * → plot datastream → open edit view" preamble doesn't get copy-pasted
 * across 15 files. The helpers assume `installMocks()` has been
 * called; they do not install mocks themselves.
 */

import { expect, type Page } from '@playwright/test'

/** Wait for the datastreams table to become visible on Home. */
export async function waitForHomeReady(page: Page): Promise<void> {
  await expect(page.getByTestId('datastreams-table')).toBeVisible({
    timeout: 30_000,
  })
}

/**
 * Pick the seeded e2e workspace if the router landed us on the
 * `/workspaces` picker. The workspace guard redirects async, so
 * `page.url()` may still show `/` when this is called immediately
 * after `page.goto('/')` — we wait for *either* the Select button or
 * the Home datastreams table and click the former if present.
 */
export async function pickWorkspaceIfNeeded(page: Page): Promise<void> {
  const pickButton = page
    .getByRole('listitem')
    .filter({ hasText: 'E2E Test Workspace' })
    .getByRole('button', { name: /^Select$/ })
  const table = page.getByTestId('datastreams-table')
  await Promise.race([
    pickButton.waitFor({ state: 'visible', timeout: 30_000 }),
    table.waitFor({ state: 'visible', timeout: 30_000 }),
  ])
  if (await pickButton.isVisible().catch(() => false)) {
    await pickButton.click()
  }
}

/** Navigate to `/`, pick the workspace, wait for Home to render. */
export async function gotoHome(page: Page): Promise<void> {
  await page.goto('/')
  await pickWorkspaceIfNeeded(page)
  await waitForHomeReady(page)
}

/**
 * Plot the first datastream in the table and wait for observations
 * to finish loading (data-loading-indicator hidden). The table is
 * virtualised but with our fixture there's only one row so the first
 * `plot-checkbox-*` element is always the target.
 */
export async function plotFirstDatastream(page: Page): Promise<void> {
  const plotBtn = page.locator('[data-testid^="plot-checkbox-"]').first()
  await expect(plotBtn).toBeVisible({ timeout: 15_000 })
  await plotBtn.click()
  await page
    .getByTestId('data-loading-indicator')
    .waitFor({ state: 'hidden', timeout: 30_000 })
}

/**
 * Full "ready to edit" preamble: home → plot → switch to edit view.
 * After this returns the EditDrawer is visible and operation panels
 * can be opened via `op-<id>` testids.
 */
export async function setupEditView(page: Page): Promise<void> {
  await gotoHome(page)
  await plotFirstDatastream(page)
  await page.getByTestId('nav-rail-item-edit').click()
  await expect(page.getByText('Data Tools')).toBeVisible()
}

/** Open an operation panel in the edit drawer by id (see operations.ts). */
export async function openOp(page: Page, id: string): Promise<void> {
  await page.getByTestId(`op-${id}`).click()
  await expect(page.getByTestId(`operation-panel-${id}`)).toBeVisible()
}

/**
 * Wait until at least `minLength` points are selected by reading the
 * dev-only `__vbwTestHooks.waitForSelectedData` installed from main.ts.
 * Use after applying a filter that should populate the store's
 * `selectedData`.
 */
export async function waitForSelection(
  page: Page,
  minLength = 1,
  timeoutMs = 10_000
): Promise<void> {
  await page.waitForFunction(
    () => typeof window.__vbwTestHooks?.waitForSelectedData === 'function',
    undefined,
    { timeout: 5_000 }
  )
  await page.evaluate(
    ([min, t]) =>
      window.__vbwTestHooks!.waitForSelectedData(min as number, t as number).then(() => {}),
    [minLength, timeoutMs]
  )
}

declare global {
  interface Window {
    __vbwTestHooks?: {
      waitForSelectedData: (
        minLength?: number,
        timeoutMs?: number
      ) => Promise<number>
    }
  }
}
