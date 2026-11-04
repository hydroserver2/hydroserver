import { expect, test, type Page } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { workspaceListItem } from '../support/ui'

const workspaceItems = '**/collections/workspaces/items?*'
const orchestrationNav = (page: Page) =>
  page.getByRole('navigation', { name: 'Job orchestration sections' })

// Hold the response explicitly so these checks reproduce slow startup reliably.
async function holdWorkspaces(page: Page, onlyAdminExpansion = false) {
  let release!: () => void
  const barrier = new Promise<void>((resolve) => {
    release = resolve
  })
  let requested!: () => void
  const requestStarted = new Promise<void>((resolve) => {
    requested = resolve
  })
  await page.route(workspaceItems, async (route) => {
    if (
      onlyAdminExpansion &&
      new URL(route.request().url()).searchParams.has('isAssociated')
    ) {
      await route.continue()
      return
    }
    const response = await route.fetch()
    requested()
    await barrier
    await route.fulfill({ response })
  })
  return { release, requestStarted }
}

test('direct orchestration links and task reloads wait for workspace access', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  const target = `/orchestration/ingestion?workspace_id=${fixtures.workspaces.private.id}`
  const initialLoad = await holdWorkspaces(page)
  await page.goto(target)
  await initialLoad.requestStarted
  await expect(page.getByText('Loading HydroServer...')).toBeVisible()
  await expect(page).toHaveURL(new RegExp(target.replace('?', '\\?')))
  initialLoad.release()
  await expect(orchestrationNav(page)).toBeVisible()
  await page.getByText(fixtures.orchestration.taskName, { exact: true }).click()
  await expect(
    page.getByRole('heading', {
      name: fixtures.orchestration.taskName,
      exact: true,
    })
  ).toBeVisible()
  const taskUrl = page.url()

  await page.unroute(workspaceItems)
  const reload = await holdWorkspaces(page)
  await page.reload()
  await reload.requestStarted
  await expect(page.getByText('Loading HydroServer...')).toBeVisible()
  await expect(page).toHaveURL(taskUrl)
  reload.release()
  await expect(
    page.getByRole('heading', {
      name: fixtures.orchestration.taskName,
      exact: true,
    })
  ).toBeVisible()
  await expect(page).toHaveURL(taskUrl)
})

test('email login returns to the requested orchestration workspace without a denial loop', async ({
  page,
}) => {
  const target = `/orchestration/quality?workspace_id=${fixtures.workspaces.private.id}`
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto(target)
  await expect(orchestrationNav(page)).toBeVisible()
  // Expire the session while retaining the page URL and saved workspace.
  await page.context().clearCookies()
  await page.reload()
  await expect(page).toHaveURL(/\/accounts\/login\//)
  const emailOption = page.getByRole('link', {
    name: 'Continue with email',
    exact: true,
  })
  if (await emailOption.isVisible()) await emailOption.click()
  await page.getByLabel('Email').fill(users.owner.email)
  await page.getByLabel('Password').fill(users.owner.password)
  const startup = await holdWorkspaces(page)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await startup.requestStarted
  await expect(page.getByText('Loading HydroServer...')).toBeVisible()
  await expect(page).toHaveURL(new RegExp(target.replace('?', '\\?')))
  startup.release()
  await expect(orchestrationNav(page)).toBeVisible()
  await expect(page.getByTestId('workspace-selector')).toContainText(
    fixtures.workspaces.private.name
  )
  await page.reload()
  await expect(orchestrationNav(page)).toBeVisible()
})

test('admin links wait for the full list of workspaces beyond their memberships', async ({
  page,
}) => {
  await authenticateSession(page, users.admin.email, users.admin.password)
  const startup = await holdWorkspaces(page, true)
  await page.goto(
    `/orchestration/ingestion?workspace_id=${fixtures.workspaces.private.id}`
  )
  await startup.requestStarted
  await expect(page.getByText('Loading HydroServer...')).toBeVisible()
  await expect(page).not.toHaveURL(/access-denied/)
  startup.release()
  await expect(orchestrationNav(page)).toBeVisible()
  await expect(page.getByTestId('workspace-selector')).toContainText(
    fixtures.workspaces.private.name
  )
})

test('workspace request failures offer retry and preserve the requested page', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.route(workspaceItems, (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Temporarily unavailable' }),
    })
  )
  await page.goto(
    `/orchestration/ingestion?workspace_id=${fixtures.workspaces.private.id}`
  )
  await expect(
    page.getByRole('heading', { name: 'Unable to load HydroServer' })
  ).toBeVisible()
  await expect(page).not.toHaveURL(/access-denied/)
  await page.unroute(workspaceItems)
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(orchestrationNav(page)).toBeVisible()
  await expect(page.getByTestId('workspace-selector')).toContainText(
    fixtures.workspaces.private.name
  )
})

test('inaccessible workspace links offer a way to recover to an available workspace', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  const target = new URL(
    `/orchestration/quality/details/quality?workspace_id=${fixtures.workspaces.admin.id}&task_id=denied-task&run_id=denied-run#details`,
    page.url()
  ).toString()
  await page.goto(target)
  await expect(
    page.getByRole('heading', {
      name: "You don't have access to this workspace",
    })
  ).toBeVisible()
  await expect(page.getByText(fixtures.workspaces.admin.id)).toBeVisible()
  await expect(page).toHaveURL(target)
  await page.reload()
  await expect(
    page.getByRole('heading', {
      name: "You don't have access to this workspace",
    })
  ).toBeVisible()
  await expect(page).toHaveURL(target)
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(
    page.getByRole('heading', {
      name: "You don't have access to this workspace",
    })
  ).toBeVisible()
  await expect(page).toHaveURL(target)
  await page.getByRole('link', { name: 'Open workspaces', exact: true }).click()
  await expect(page).toHaveURL(/\/workspaces(?:\?.*)?$/)
  await page
    .getByRole('link', { name: 'Job orchestration', exact: true })
    .click()
  await expect(orchestrationNav(page)).toBeVisible()
})

test('users without workspaces see workspace guidance instead of access denied', async ({
  page,
}) => {
  await authenticateSession(page, users.deleteMe.email, users.deleteMe.password)
  await page.goto('/orchestration/ingestion')
  await expect(page.getByTestId('no-selected-workspace')).toBeVisible()
  await expect(page).not.toHaveURL(/access-denied/)
})

test('retry opens the original task link after workspace access is granted', async ({
  page,
  browser,
}) => {
  const ownerContext = await browser.newContext()
  try {
    const ownerPage = await ownerContext.newPage()
    await authenticateSession(
      ownerPage,
      users.owner.email,
      users.owner.password
    )
    await ownerPage.goto(
      `/orchestration/ingestion?workspace_id=${fixtures.workspaces.private.id}`
    )
    await ownerPage
      .getByText(fixtures.orchestration.taskName, { exact: true })
      .click()
    await expect(
      ownerPage.getByRole('heading', {
        name: fixtures.orchestration.taskName,
        exact: true,
      })
    ).toBeVisible()
    const target = ownerPage.url()

    await authenticateSession(
      page,
      users.deleteMe.email,
      users.deleteMe.password
    )
    await page.goto(target)
    await expect(
      page.getByRole('heading', {
        name: "You don't have access to this workspace",
      })
    ).toBeVisible()
    await expect(page).toHaveURL(target)

    await ownerPage.goto('/workspaces')
    await workspaceListItem(ownerPage, fixtures.workspaces.private.name).click()
    await ownerPage.getByRole('tab', { name: 'Collaborators' }).click()
    await ownerPage.getByTestId('add-collaborator-button').click()
    await ownerPage
      .getByLabel("New collaborator's email")
      .fill(users.deleteMe.email)
    await ownerPage.getByTestId('new-collaborator-role').click()
    await ownerPage.getByRole('option', { name: /Viewer/ }).click()
    await ownerPage.getByTestId('submit-collaborator-button').click()
    await expect(
      ownerPage.getByTestId(`collaborator-row-${users.deleteMe.email}`)
    ).toBeVisible()

    await page.getByRole('button', { name: 'Try again', exact: true }).click()
    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.taskName,
        exact: true,
      })
    ).toBeVisible()
    await expect(page).toHaveURL(target)
  } finally {
    await ownerContext.close()
  }
})
