import { expect, Locator, Page } from '@playwright/test'

function overlayOptions(page: Page) {
  return page
    .locator('.v-overlay-container [role="option"], .v-overlay-container .v-list-item')
    .filter({ hasNot: page.locator('[aria-hidden="true"]') })
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
  const field = page.getByRole('combobox', { name: label }).first()
  await field.click()
  await field.fill(value)
  await field.press('Enter')
}

export async function clickWorkspaceTableAction(
  page: Page,
  action: 'access-control' | 'edit' | 'delete',
  workspaceId: string
) {
  await page
    .getByTestId(`workspace-${action}-${workspaceId}`)
    .click()
}

export async function waitForSnackbar(page: Page, text: string | RegExp) {
  await expect(page.getByText(text).first()).toBeVisible()
}

export async function maybeDismissDialog(dialog: Locator) {
  if (await dialog.isVisible()) {
    await dialog.getByRole('button', { name: 'Close' }).click()
  }
}
