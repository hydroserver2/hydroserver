import { expect, test } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'

test('derivation sources use the same three-line card and menu, with links to their own site', async ({
  page,
}, testInfo) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto(
    `/orchestration/aggregation?workspace_id=${fixtures.workspaces.private.id}&site_id=${fixtures.monitoringSites.private.id}`
  )
  await page
    .getByRole('button', {
      name: fixtures.orchestration.aggregationTaskName,
      exact: true,
    })
    .click()
  await expect(
    page.getByRole('heading', {
      name: fixtures.orchestration.aggregationTaskName,
      exact: true,
    })
  ).toBeVisible()
  const taskId = new URL(page.url()).searchParams.get('task_id')!
  const collectionUrl = `${apiBaseUrl}/api/ogc/collections/data-product-transformations/items`
  const response = await page.request.get(collectionUrl, { params: { taskId } })
  expect(response.ok()).toBeTruthy()
  const [transformation] = (await response.json()).data
  const csrfToken = (await page.context().cookies(apiBaseUrl)).find(
    (cookie) => cookie.name === 'csrftoken'
  )!.value
  const headers = { 'X-CSRFToken': csrfToken }
  // Convert only this isolated test scenario's seeded task to a derivation.
  const removed = await page.request.delete(
    `${collectionUrl}/${transformation.id}`,
    { headers }
  )
  expect(removed.ok()).toBeTruthy()
  const created = await page.request.post(collectionUrl, {
    headers,
    data: {
      taskId,
      transformationType: 'derivation',
      outputDatastreamId: transformation.outputDatastreamId,
      inputDatastreams: [
        {
          datastreamId: fixtures.datastreams.privateWorkspacePublic.id,
          variableName: 'x',
        },
      ],
      formula: 'x * 2',
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const detailUrl = `/orchestration/aggregation/details/derivation?workspace_id=${fixtures.workspaces.private.id}&site_id=${fixtures.monitoringSites.private.id}&task_id=${taskId}`
  await page.goto(detailUrl)
  await page.getByRole('tab', { name: 'Mappings' }).click()
  const card = page.locator('.product-mapping-source .mapping-datastream-card')
  await expect(card.locator('.mapping-datastream-card__name')).toHaveText(
    fixtures.datastreams.privateWorkspacePublic.name
  )
  await expect(card.locator('.mapping-datastream-card__site')).toHaveText(
    `@ ${fixtures.monitoringSites.privateWorkspacePublic.name}`
  )
  await expect(
    card.locator('.mapping-datastream-card__text > span')
  ).toHaveCount(3)
  await expect(card).not.toContainText('Variable x')
  const id = fixtures.datastreams.privateWorkspacePublic.id
  await expect(card.locator('.mapping-datastream-card__id')).toHaveText(id)
  await card.getByTestId(`datastream-links-${id}`).click()
  await expect(
    page.getByTestId(`view-site-for-datastream-${id}`)
  ).toHaveAttribute(
    'href',
    `/sites/${fixtures.monitoringSites.privateWorkspacePublic.id}?datastream=${id}`
  )
  await expect(page.getByTestId(`visualize-datastream-${id}`)).toHaveAttribute(
    'href',
    `/visualize-data?sites=${fixtures.monitoringSites.privateWorkspacePublic.id}&datastreams=${id}`
  )
  await page.screenshot({
    path: testInfo.outputPath('derivation-mapping-menu.png'),
    fullPage: true,
    animations: 'disabled',
  })
  await page.getByTestId(`view-site-for-datastream-${id}`).click()
  await expect(page).toHaveURL(
    new RegExp(
      `/sites/${fixtures.monitoringSites.privateWorkspacePublic.id}\\?datastream=${id}$`
    )
  )
  await expect(
    page.getByRole('heading', {
      name: fixtures.monitoringSites.privateWorkspacePublic.name,
      exact: true,
    })
  ).toBeVisible()
  await page.goto(detailUrl)
  await page.getByRole('tab', { name: 'Mappings' }).click()
  await card.getByTestId(`datastream-links-${id}`).click()
  await page.getByTestId(`visualize-datastream-${id}`).click()
  await expect(page).toHaveURL(
    (url) =>
      url.pathname === '/visualize-data' &&
      url.searchParams.get('sites') ===
        fixtures.monitoringSites.privateWorkspacePublic.id &&
      url.searchParams.get('datastreams') === id
  )
  await expect(
    page.getByRole('checkbox', {
      name: `Plot ${fixtures.datastreams.privateWorkspacePublic.name}`,
      exact: true,
    })
  ).toBeChecked()
})

for (const kind of ['aggregation', 'quality'] as const) {
  test(`${kind} targets load their names, site, UUID, and both menu links from a copied task URL`, async ({
    page,
  }, testInfo) => {
    const taskName =
      kind === 'aggregation'
        ? fixtures.orchestration.aggregationTaskName
        : fixtures.orchestration.monitoringTaskName
    const targetName =
      kind === 'aggregation'
        ? 'Private Aggregation Output'
        : 'Private Monitoring Rule Datastream'
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(
      `/orchestration/${kind}?workspace_id=${fixtures.workspaces.private.id}&site_id=${fixtures.monitoringSites.private.id}`
    )
    await page.getByRole('button', { name: taskName, exact: true }).click()
    await expect(
      page.getByRole('heading', { name: taskName, exact: true })
    ).toBeVisible()
    await page.goto(page.url())
    await page.getByRole('tab', { name: 'Mappings' }).click()

    const card = page.locator(
      '.product-mapping-target .mapping-datastream-card, .quality-mapping-target .mapping-datastream-card'
    )
    await expect(card).toHaveCount(1)
    await expect(card.locator('.mapping-datastream-card__name')).toContainText(
      targetName
    )
    await expect(card.locator('.mapping-datastream-card__site')).toHaveText(
      `@ ${fixtures.monitoringSites.private.name}`
    )
    await expect(
      card.locator('.mapping-datastream-card__text > span')
    ).toHaveCount(3)
    const id = (
      await card.locator('.mapping-datastream-card__id').innerText()
    ).trim()
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    )
    await card.getByTestId(`datastream-links-${id}`).click()
    await expect(
      page.getByTestId(`view-site-for-datastream-${id}`)
    ).toHaveAttribute(
      'href',
      `/sites/${fixtures.monitoringSites.private.id}?datastream=${id}`
    )
    const visualizeLink = await page
      .getByTestId(`visualize-datastream-${id}`)
      .getAttribute('href')
    const url = new URL(visualizeLink!, page.url())
    expect(url.pathname).toBe('/visualize-data')
    expect(url.searchParams.get('sites')).toBe(
      fixtures.monitoringSites.private.id
    )
    expect(url.searchParams.get('datastreams')).toBe(id)
    await page.keyboard.press('Escape')
    await expect(
      page.getByTestId(`view-site-for-datastream-${id}`)
    ).toBeHidden()
    await page.screenshot({
      path: testInfo.outputPath(`${kind}-target-desktop.png`),
      fullPage: true,
      animations: 'disabled',
    })
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(card).toBeVisible()
    await expect(
      card.locator('.mapping-datastream-card__text > span')
    ).toHaveCount(3)
    await page.screenshot({
      path: testInfo.outputPath(`${kind}-target-mobile.png`),
      fullPage: true,
      animations: 'disabled',
    })
  })
}
