import { expect, Locator, Page } from '@playwright/test'

function overlayOptions(page: Page) {
  return page.locator(
    '.v-overlay-container [role="option"]:visible, ' +
      '.v-overlay-container .v-list-item:visible, ' +
      '[role="listbox"] [role="option"]:visible, ' +
      '[role="listbox"] .v-list-item:visible'
  )
}

export async function chooseOverlayOption(page: Page, text: string) {
  const option = overlayOptions(page).filter({ hasText: text }).first()
  await expect(option).toBeVisible()
  await option.click()
}

export async function selectWorkspace(page: Page, workspaceName: string) {
  await page.getByTestId('workspace-selector').click()
  await chooseOverlayOption(page, workspaceName)
  await expect(page.getByTestId('workspace-selector')).toContainText(
    workspaceName
  )
}

export async function chooseAutocompleteOption(
  page: Page,
  label: string,
  optionText: string
) {
  const field = page.getByRole('combobox', { name: label }).first()
  await field.click()
  await field.fill(optionText)
  await chooseOverlayOption(page, optionText)
}

export async function fillCombobox(page: Page, label: string, value: string) {
  const combobox = page.getByRole('combobox', { name: label }).first()
  const textbox = page.getByRole('textbox', { name: label }).first()
  const field = (await combobox.count()) > 0 ? combobox : textbox

  await expect(field).toBeVisible()
  await field.click()
  await field.fill(value)

  if ((await combobox.count()) > 0) {
    await field.press('Enter')
  }
}

/** A workspace entry in the master list of the Manage Workspaces page. */
export function workspaceListItem(page: Page, workspaceName: string) {
  return page
    .locator('[data-testid^="workspace-list-item-"]')
    .filter({ hasText: workspaceName })
    .first()
}

export async function createWorkspaceFromManagePage(
  page: Page,
  workspaceName: string
) {
  await page.getByRole('button', { name: 'Add workspace', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Name *').fill(workspaceName)
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(workspaceListItem(page, workspaceName)).toBeVisible()
}

export async function deleteWorkspaceFromManagePage(
  page: Page,
  workspaceName: string
) {
  const item = workspaceListItem(page, workspaceName)
  await expect(item).toBeVisible()
  await item.locator('[data-testid^="workspace-delete-"]').click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Workspace name').fill(workspaceName)
  await dialog.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(workspaceListItem(page, workspaceName)).toHaveCount(0)
}

export async function waitForSnackbar(page: Page, text: string | RegExp) {
  await expect(page.getByText(text).first()).toBeVisible()
}

export async function maybeDismissDialog(dialog: Locator) {
  if (await dialog.isVisible()) {
    await dialog.getByRole('button', { name: 'Close' }).click()
  }
}
