import { expect, test, type Page } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

const menuSelector = '.hs-table-filter-menu:visible'

for (const mode of ['signed out', 'signed in without memberships'] as const) {
  test(`visualization offers public workspaces when ${mode}`, async ({
    page,
  }) => {
    if (mode === 'signed in without memberships') {
      await authenticateSession(
        page,
        users.limited.email,
        users.limited.password
      )
    }
    await page.goto('/visualize-data')
    const trigger = page.getByRole('button', { name: /^Filter by workspaces/ })
    await trigger.click()
    const menu = page.locator(menuSelector)
    const publicWorkspace = menu.getByRole('checkbox', {
      name: `Workspaces: ${fixtures.workspaces.public.name}`,
      exact: true,
    })
    await expect(publicWorkspace).toBeVisible()
    await expect(
      menu.getByRole('checkbox', {
        name: `Workspaces: ${fixtures.workspaces.private.name}`,
        exact: true,
      })
    ).toHaveCount(0)
    await publicWorkspace.click()
    await page.keyboard.press('Escape')
    await expect(menu).toBeHidden()
    await expect(trigger).toHaveAttribute(
      'aria-label',
      'Filter by workspaces (1 selected)'
    )
    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await page.reload()
    await expect(trigger).toHaveAttribute(
      'aria-label',
      'Filter by workspaces (1 selected)'
    )
    await trigger.click()
    await expect(
      menu.locator('.hs-table-filter-menu__selected').getByRole('checkbox', {
        name: `Workspaces: ${fixtures.workspaces.public.name}`,
        exact: true,
      })
    ).toBeChecked()

    if (mode === 'signed in without memberships') {
      await page.keyboard.press('Escape')
      await page.goto('/workspaces')
      await expect(
        page.getByRole('heading', {
          name: 'No workspaces available',
          exact: true,
        })
      ).toBeVisible()
      await expect(
        page.getByTestId(`workspace-list-item-${fixtures.workspaces.public.id}`)
      ).toHaveCount(0)
    }
  })
}

test('visualization refresh restores the filter badge, menu selection, query, and results with late workspace data', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto('/visualize-data')
  const trigger = page.getByRole('button', { name: /^Filter by workspaces/ })
  await trigger.click()
  await page
    .locator(menuSelector)
    .getByRole('checkbox', {
      name: `Workspaces: ${fixtures.workspaces.private.name}`,
      exact: true,
    })
    .click()
  await page.keyboard.press('Escape')
  await expect(page.locator(menuSelector)).toBeHidden()
  await expect(trigger).toHaveAttribute(
    'aria-label',
    'Filter by workspaces (1 selected)'
  )
  const search = page.getByRole('combobox', { name: 'Search', exact: true })
  const query = await search.inputValue()
  await expect(page).toHaveURL(/q=/)

  let releaseWorkspaces!: () => void
  const workspaceGate = new Promise<void>((resolve) => {
    releaseWorkspaces = resolve
  })
  await page.route(
    '**/api/ogc/collections/workspaces/items?**',
    async (route) => {
      if (
        new URL(route.request().url()).searchParams.get('isAssociated') ===
        'true'
      )
        await workspaceGate
      await route.continue()
    }
  )
  const workspaceResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/ogc/collections/workspaces/items?') &&
      new URL(response.url()).searchParams.get('isAssociated') === 'true'
  )
  try {
    await page.reload({ waitUntil: 'domcontentloaded' })
    // Visualization must not depend on the associated-workspace management list.
    await expect(trigger).toBeVisible()
    await expect(trigger).toHaveAttribute(
      'aria-label',
      'Filter by workspaces (1 selected)'
    )
    releaseWorkspaces()
    await workspaceResponse
    await expect(trigger).toHaveAttribute(
      'aria-label',
      'Filter by workspaces (1 selected)'
    )
    await expect(trigger.locator('.filter-count')).toHaveText('1')
    await expect(search).toHaveValue(query)
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.privateWorkspacePublic.id}`
      )
    ).toBeVisible()
    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toHaveCount(0)
    await trigger.click()
    await expect(
      page
        .locator(menuSelector)
        .locator('.hs-table-filter-menu__selected')
        .getByRole('checkbox', {
          name: `Workspaces: ${fixtures.workspaces.private.name}`,
          exact: true,
        })
    ).toBeChecked()
  } finally {
    releaseWorkspaces()
  }
})

async function assertFixedHeader(page: Page) {
  const menu = page.locator(menuSelector)
  const header = menu.locator('header')
  await header.getByRole('textbox').click()
  const before = await header.boundingBox()
  const list = menu.locator('.hs-table-filter-menu__options')
  await list.evaluate((element) => {
    element.scrollTop = element.scrollHeight
  })
  expect(await list.evaluate((element) => element.scrollTop)).toBeGreaterThan(0)
  expect(await header.boundingBox()).toEqual(before)
  await expect(header.getByRole('textbox')).toBeInViewport()
}

test('long filter menus keep the title and search fixed and selected options available to remove individually', async ({
  page,
}, testInfo) => {
  await page.route(
    '**/api/ogc/collections/workspaces/items/*/collaborators?**',
    async (route) => {
      const response = await route.fetch()
      const body = await response.json()
      const sample = body.included.users[0]
      const users = Array.from({ length: 30 }, (_, index) => ({
        ...sample,
        email: `menu-${index}@example.invalid`,
        name: `Collaborator ${index}`,
        organizationName: `Organization ${String(index + 1).padStart(2, '0')}`,
      }))
      body.included.users = users
      body.data = users.map((user) => ({
        roleId: body.included.roles[0].id,
        userEmail: user.email,
        serviceAccountEmail: null,
      }))
      await route.fulfill({ response, json: body })
    }
  )
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto(
    `/workspaces?workspace=${fixtures.workspaces.public.id}&section=collaborators`
  )
  const trigger = page.getByRole('button', { name: /^Filter by organization/ })
  await trigger.click()
  const menu = page.locator(menuSelector)
  await assertFixedHeader(page)
  await menu
    .getByRole('checkbox', {
      name: 'Organization: Organization 30',
      exact: true,
    })
    .check()
  await page.keyboard.press('Escape')
  await expect(menu).toBeHidden()
  await trigger.click()
  await expect(trigger).toHaveAttribute('aria-expanded', 'true')
  await expect(
    menu.locator('.hs-table-filter-menu__selected').getByRole('checkbox', {
      name: 'Organization: Organization 30',
      exact: true,
    })
  ).toBeChecked()
  await expect
    .poll(() =>
      menu
        .locator('.hs-table-filter-menu__options')
        .evaluate((element) => element.scrollTop)
    )
    .toBe(0)
  await menu.getByRole('textbox').fill('Organization 29')
  await expect(
    menu.getByRole('checkbox', {
      name: 'Organization: Organization 30',
      exact: true,
    })
  ).toBeVisible()
  await menu
    .getByRole('checkbox', {
      name: 'Organization: Organization 29',
      exact: true,
    })
    .check()
  await expect(
    menu.locator('.hs-table-filter-menu__selected').getByRole('checkbox')
  ).toHaveCount(1)
  await menu
    .getByRole('checkbox', {
      name: 'Organization: Organization 30',
      exact: true,
    })
    .click()
  await expect(
    menu.locator('.hs-table-filter-menu__selected').getByRole('checkbox')
  ).toHaveCount(1)
  await expect(
    menu.getByRole('checkbox', {
      name: 'Organization: Organization 29',
      exact: true,
    })
  ).toBeChecked()
  await expect(menu.getByText('Clear filter', { exact: true })).toHaveCount(0)
  await menu.getByRole('textbox').fill('')
  await page.keyboard.press('Escape')
  await expect(menu).toBeHidden()
  await trigger.click()
  await expect(trigger).toHaveAttribute('aria-expanded', 'true')
  const firstBanner = menu
    .locator('.hs-table-filter-menu__section-title')
    .first()
  await expect(firstBanner).toHaveText('Selected organizations')
  await expect(
    menu.locator(
      '.hs-table-filter-menu__available .hs-table-filter-menu__section-title'
    )
  ).toHaveText('Organizations')
  await menu.getByRole('textbox').click()
  const gap = await menu.evaluate((element) => {
    const header = element.querySelector('header')!.getBoundingClientRect()
    const banner = element
      .querySelector('.hs-table-filter-menu__section-title')!
      .getBoundingClientRect()
    return banner.top - header.bottom
  })
  expect(Math.abs(gap)).toBeLessThan(1)
  const rows = menu.locator('.hs-table-filter-menu__option')
  for (const row of [rows.first(), rows.nth(1)]) {
    await row.hover()
    await expect(row).toHaveCSS('background-color', 'rgb(255, 255, 255)')
  }
  await page.screenshot({
    path: testInfo.outputPath('filter-selected-desktop.png'),
    animations: 'disabled',
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await assertFixedHeader(page)
  await page.screenshot({
    path: testInfo.outputPath('filter-header-mobile.png'),
    animations: 'disabled',
  })
})

for (const context of [
  'visualization',
  'site datastreams',
  'datastream picker',
  'collaborator roles',
  'service-account roles',
  'task status',
  'task type',
] as const) {
  test(`${context} filters group selections and deselect individually`, async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    let trigger
    if (context === 'visualization') {
      await page.goto('/visualize-data')
      trigger = page.getByRole('button', { name: /^Filter by workspaces/ })
    } else if (context === 'site datastreams') {
      await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)
      trigger = page.getByRole('button', { name: /^Filter by unit/ })
    } else if (
      context === 'collaborator roles' ||
      context === 'service-account roles'
    ) {
      const section =
        context === 'collaborator roles' ? 'collaborators' : 'service-accounts'
      await page.goto(
        `/workspaces?workspace=${fixtures.workspaces.public.id}&section=${section}`
      )
      trigger = page.getByRole('button', { name: /^Filter by role/ })
    } else if (context === 'task type') {
      await page.goto(
        `/orchestration/aggregation?workspace_id=${fixtures.workspaces.private.id}&site_id=${fixtures.monitoringSites.private.id}`
      )
      trigger = page.getByRole('button', { name: /^Filter by task type/ })
    } else {
      await page.goto(
        `/orchestration/ingestion?workspace_id=${fixtures.workspaces.private.id}`
      )
      if (context === 'datastream picker') {
        await page
          .getByRole('button', {
            name: fixtures.orchestration.taskName,
            exact: true,
          })
          .click()
        await page.getByRole('button', { name: 'Edit', exact: true }).click()
        await page.locator('.datastream-card-selector__button').click()
        trigger = page
          .locator('.datastream-header-filters')
          .getByRole('button', { name: /^Unit/ })
      } else trigger = page.getByRole('button', { name: /^Filter by status/ })
    }
    await trigger.click()
    const menu = page.locator(menuSelector)
    const role = context === 'task status' ? 'menuitemcheckbox' : 'checkbox'
    const first = menu
      .locator('.hs-table-filter-menu__available')
      .getByRole(role)
      .first()
    await expect(first).toBeVisible()
    await expect(
      menu.locator('.hs-table-filter-menu__section-title')
    ).toHaveCount(0)
    await first.click()
    if (context === 'task status')
      await expect(first).toHaveAttribute('aria-checked', 'true')
    else await expect(first).toBeChecked()
    const selected = menu
      .locator('.hs-table-filter-menu__selected')
      .getByRole(role)
    await expect(selected).toHaveCount(0)
    await page.keyboard.press('Escape')
    await expect(menu).toBeHidden()
    await trigger.click()
    await expect(trigger).toHaveAttribute('aria-expanded', 'true')
    await expect(selected).toHaveCount(1)
    const sectionLabel = {
      visualization: 'Workspaces',
      'site datastreams': 'Units',
      'datastream picker': 'Units',
      'collaborator roles': 'Roles',
      'service-account roles': 'Roles',
      'task status': 'Statuses',
      'task type': 'Task types',
    }[context]
    await expect(
      menu.getByText(`Selected ${sectionLabel.toLowerCase()}`, { exact: true })
    ).toBeVisible()
    await expect(menu.getByText(sectionLabel, { exact: true })).toBeVisible()
    if (context === 'visualization') {
      await menu.getByRole('textbox').click()
      await page.screenshot({
        path: test.info().outputPath('workspace-filter-polished.png'),
        animations: 'disabled',
      })
    }
    await selected.click()
    await expect(selected).toHaveCount(1)
    if (context === 'task status')
      await expect(selected).toHaveAttribute('aria-checked', 'false')
    else await expect(selected).not.toBeChecked()
    await page.keyboard.press('Escape')
    await expect(menu).toBeHidden()
    await trigger.click()
    await expect(trigger).toHaveAttribute('aria-expanded', 'true')
    await expect(selected).toHaveCount(0)
    await expect(menu.getByText('Clear filter', { exact: true })).toHaveCount(0)
    await expect(
      menu.locator('.hs-table-filter-menu__section-title')
    ).toHaveCount(0)
    await expect(menu).toBeVisible()
  })
}
