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
  const container = field.locator('xpath=ancestor::*[@role="combobox"][1]')
  await expect(field).toBeVisible()
  await container.scrollIntoViewIfNeeded()
  const toggle = container.getByRole('button').last()
  if ((await toggle.count()) > 0) {
    await toggle.click({ force: true })
  }
  await field.evaluate((element) => {
    ;(element as HTMLInputElement).focus()
  })
  await page.keyboard.press('Control+A')
  await page.keyboard.press('Backspace')
  await page.keyboard.type(optionText)
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
