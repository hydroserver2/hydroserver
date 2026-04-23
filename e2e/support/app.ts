/**
 * Flow helpers shared by every mocked e2e spec.
 *
 * Specs should usually go through these so the "boot → pick workspace
 * → plot datastream → open edit view" preamble doesn't get copy-pasted
 * across 15 files. The helpers assume `installMocks()` has been
 * called; they do not install mocks themselves.
 */

import { expect, type Page } from '@playwright/test'
import { WORKSPACE_ID } from './fixtures'

/** Wait for the datastreams table to become visible on Home. */
export async function waitForHomeReady(page: Page): Promise<void> {
  await expect(page.getByTestId('datastreams-table')).toBeVisible({
    timeout: 30_000,
  })
}

/**
 * Pre-seed the workspace store so the router's `hasWorkspaceGuard`
 * passes on the very first navigation and the picker is skipped
 * entirely. Relying on the UI to click the Select button is fragile
 * cross-browser (Firefox in particular sometimes swallows the click
 * when the v-list-item row and its nested Select button both register
 * click handlers). Seeding storage sidesteps the picker entirely —
 * equivalent to a user who already chose a workspace in a previous
 * session.
 *
 * The payload shape mirrors what pinia-plugin-persistedstate writes
 * for the `workspaces` store (configured in `store/workspaces.ts`
 * with `key: 'qc-app.selected-workspace'`, `pick: ['selectedWorkspace']`).
 */
export async function seedWorkspaceSelection(page: Page): Promise<void> {
  const workspace = {
    id: WORKSPACE_ID,
    name: 'E2E Test Workspace',
    isPrivate: false,
    owner: { name: 'Test User', email: 'test@example.com' },
    collaboratorRole: {
      name: 'owner',
      permissions: [{ action: '*', resource: '*' }],
    },
  }
  await page.addInitScript(
    ({ ws }) => {
      try {
        localStorage.setItem(
          'qc-app.selected-workspace',
          JSON.stringify({ selectedWorkspace: ws })
        )
      } catch {
        // storage disabled — fall back to UI flow
      }
    },
    { ws: workspace }
  )
}

/**
 * Pick the seeded e2e workspace if the router landed us on the
 * `/workspaces` picker. With `seedWorkspaceSelection` running in an
 * init script before `page.goto`, the picker is usually skipped and
 * the datastreams table shows up directly. This helper remains as a
 * belt-and-braces fallback for cases where the seed didn't land
 * (e.g. a test running in a context without localStorage).
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
    // `force: true` bypasses Firefox's occasional "actionability"
    // stall on Vuetify buttons that sit inside clickable list items.
    await pickButton.click({ force: true })
  }
}

/** Navigate to `/`, pick the workspace, wait for Home to render. */
export async function gotoHome(page: Page): Promise<void> {
  await seedWorkspaceSelection(page)
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
