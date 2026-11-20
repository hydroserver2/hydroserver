import { expect, test, type Page } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

const api = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
const collection = (name: string) => `${api}/api/ogc/collections/${name}/items`

async function seedRows(page: Page) {
  const response = await page.request.get(
    `${collection('datastreams')}/${fixtures.datastreams.public.id}`
  )
  expect(response.ok()).toBeTruthy()
  const { data: template } = await response.json()
  const csrf =
    (await page.context().cookies(api)).find(
      (cookie) => cookie.name === 'csrftoken'
    )?.value ?? ''
  const headers = { 'X-CSRFToken': csrf, Referer: api }
  const fields = [
    'description',
    'type',
    'sampledMedium',
    'noDataValue',
    'aggregationStatistic',
    'timeAggregationInterval',
    'timeAggregationIntervalUnit',
    'monitoringSiteId',
    'methodId',
    'observedPropertyId',
    'processingLevelId',
    'unitId',
  ]
  const body = Object.fromEntries(
    fields.map((field) => [field, template[field]])
  )
  for (let index = 0; index < 31; index++) {
    const name = `Paging stream ${String(index).padStart(2, '0')}`
    const created = await page.request.post(collection('datastreams'), {
      headers,
      data: { ...body, name },
    })
    expect(created.ok(), await created.text()).toBeTruthy()
  }
}

async function reachNextPage(page: Page, offsets: number[]) {
  await expect
    .poll(async () => {
      if (offsets.includes(25)) return true
      await page
        .locator('.load-more-row')
        .filter({ visible: true })
        .last()
        .scrollIntoViewIfNeeded()
      return offsets.includes(25)
    })
    .toBe(true)
}

test('visualization paginates server results, retains filters and preserves plotted selections', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  await seedRows(page)
  const offsets: number[] = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (
      url.pathname.endsWith('/datastreams/items') &&
      url.searchParams.get('limit') === '25'
    )
      offsets.push(Number(url.searchParams.get('offset')))
  })
  await page.goto(
    `/visualize-data?sites=${fixtures.monitoringSites.public.id}&plot=false`
  )
  const visSearch = page.getByRole('combobox', { name: 'Search', exact: true })
  offsets.length = 0
  await visSearch.fill('Paging stream')
  await expect(page.locator('.datastreams-count')).toHaveText('31 available')
  await reachNextPage(page, offsets)
  await visSearch.fill('Paging stream sort:name-desc')
  await expect(
    page.locator('[data-testid^="plot-datastream-"]').first()
  ).toHaveAccessibleName('Plot Paging stream 30')
  await visSearch.fill('Paging stream 30')
  await expect(page.locator('.datastreams-count')).toHaveText('1 available')
  await page
    .getByRole('checkbox', { name: 'Plot Paging stream 30', exact: true })
    .check()
  await expect(page.getByTestId('datastream-selection-bar')).toContainText(
    '1 selected for plotting (maximum 5)'
  )
  await expect(
    page.getByRole('button', { name: /Filter by sites/i })
  ).toBeVisible()
  await visSearch.fill('Paging stream 00')
  await expect(
    page.getByRole('checkbox', { name: 'Plot Paging stream 00', exact: true })
  ).toBeVisible()
  await expect(
    page.getByRole('checkbox', { name: 'Plot Paging stream 30', exact: true })
  ).toHaveCount(0)
  await page.getByTestId('toggle-selected-datastreams').click()
  await expect(
    page.getByRole('checkbox', { name: 'Plot Paging stream 30', exact: true })
  ).toBeChecked()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByTestId('datastream-selection-bar')).toBeVisible()
  await expect(page.getByTestId('toggle-selected-datastreams')).toBeVisible()
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth
    )
  ).toBe(true)
})

test('workspace metadata searches across server pages and resets the offset', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  const csrf =
    (await page.context().cookies(api)).find(
      (cookie) => cookie.name === 'csrftoken'
    )?.value ?? ''
  const response = await page.request.get(
    `${collection('methods')}/${fixtures.metadata.privateAssignedMethod.id}`
  )
  const { data: template } = await response.json()
  for (let index = 0; index < 31; index++) {
    const created = await page.request.post(collection('methods'), {
      headers: { 'X-CSRFToken': csrf, Referer: api },
      data: {
        workspaceId: fixtures.workspaces.private.id,
        name: `Paging metadata ${String(index).padStart(2, '0')}`,
        description: 'Pagination test method',
        type:
          typeof template.type === 'string'
            ? template.type
            : template.type.name,
      },
    })
    expect(created.ok(), await created.text()).toBeTruthy()
  }
  const offsets: number[] = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (
      url.pathname.endsWith('/methods/items') &&
      url.searchParams.get('limit') === '25'
    )
      offsets.push(Number(url.searchParams.get('offset')))
  })
  await page.goto(
    `/workspaces?workspace=${fixtures.workspaces.private.id}&section=metadata`
  )
  await page.getByRole('tab', { name: 'Methods', exact: true }).click()
  const search = page.getByRole('textbox', {
    name: 'Search metadata…',
    exact: true,
  })
  await search.fill('Paging metadata')
  await expect(
    page.getByText('Paging metadata 00', { exact: true })
  ).toBeVisible()
  await reachNextPage(page, offsets)
  await search.fill('Paging metadata 30')
  await expect(
    page.getByText('Paging metadata 30', { exact: true })
  ).toBeVisible()
  await expect(
    page.getByText('Paging metadata 00', { exact: true })
  ).toHaveCount(0)
  expect(offsets.at(-1)).toBe(0)
})

test('visualization retries failed filter loading without losing the bookmarked query', async ({
  page,
}) => {
  let fail = true
  await page.route('**/collections/methods/items?*', async (route) => {
    if (fail) {
      fail = false
      await route.fulfill({
        status: 500,
        json: { message: 'Internal Server Error' },
      })
    } else await route.continue()
  })
  const query = `sites=${fixtures.monitoringSites.public.id}&q=Public&plot=false`
  await page.goto(`/visualize-data?${query}`)
  const error = page.getByTestId('visualization-load-error')
  await expect(error).toContainText('Unable to load visualization filters')
  expect(new URL(page.url()).searchParams.get('q')).toBe('Public')
  await error.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(error).toHaveCount(0)
  await expect(
    page.getByRole('combobox', { name: 'Search', exact: true })
  ).toHaveValue(`site:"${fixtures.monitoringSites.public.name}" Public`)
  await expect(
    page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: /Filter by sites/i })
  ).toContainText('1')
})

for (const kind of ['visualization', 'metadata'] as const) {
  test(`${kind} can retry a failed first page`, async ({ page }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    let fail = true
    const collectionName = kind === 'visualization' ? 'datastreams' : 'methods'
    await page.route(
      `**/collections/${collectionName}/items?*`,
      async (route) => {
        const url = new URL(route.request().url())
        if (fail && url.searchParams.get('limit') === '25') {
          fail = false
          await route.fulfill({
            status: 500,
            json: { message: 'Internal Server Error' },
          })
        } else await route.continue()
      }
    )
    await page.goto(
      kind === 'visualization'
        ? `/visualize-data?sites=${fixtures.monitoringSites.public.id}&plot=false`
        : `/workspaces?workspace=${fixtures.workspaces.private.id}&section=metadata`
    )
    if (kind === 'metadata')
      await page.getByRole('tab', { name: 'Methods', exact: true }).click()
    const retry = page
      .locator('.load-more-row')
      .getByRole('button', { name: 'Retry', exact: true })
    await expect(retry).toBeVisible()
    await retry.click()
    await expect(retry).toHaveCount(0)
    if (kind === 'visualization')
      await expect(
        page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
      ).toBeVisible()
    else
      await expect(
        page.getByTestId(
          `view-metadata-${fixtures.metadata.privateAssignedMethod.id}`
        )
      ).toBeVisible()
  })
}

test('mobile metadata follows page scrolling and fetches only the next 25 rows when needed', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  const offsets: number[] = []
  const rows = Array.from({ length: 125 }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
    workspaceId: fixtures.workspaces.private.id,
    name: `Mobile method ${String(index).padStart(3, '0')}`,
    code: `M${index}`,
    type: 'Generic',
    description: 'Mobile pagination regression',
  }))
  await page.route('**/collections/methods/items?*', async (route) => {
    const url = new URL(route.request().url())
    if (url.searchParams.get('limit') !== '25') return route.continue()
    const offset = Number(url.searchParams.get('offset'))
    offsets.push(offset)
    await route.fulfill({
      json: {
        data: rows.slice(offset, offset + 25),
        meta: { numberMatched: rows.length },
      },
    })
  })
  await page.goto(
    `/workspaces?workspace=${fixtures.workspaces.private.id}&section=metadata`
  )
  await page.getByRole('tab', { name: 'Methods', exact: true }).click()
  await expect(
    page.getByText('Mobile method 000', { exact: true })
  ).toBeVisible()
  // Let automatic loading settle so eager requests cannot escape this check.
  await page.waitForLoadState('networkidle')
  expect(offsets).toEqual([0])

  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForLoadState('networkidle')
  expect(offsets).toEqual([0])
  const wrapper = page.locator('.metadata-items .v-table__wrapper')
  expect(
    await wrapper.evaluate(
      (element) => element.scrollHeight <= element.clientHeight + 1
    )
  ).toBe(true)

  for (const offset of [25, 50]) {
    const nextPage = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return (
        url.pathname.endsWith('/methods/items') &&
        url.searchParams.get('offset') === String(offset)
      )
    })
    await page
      .locator('.metadata-items .load-more-row')
      .scrollIntoViewIfNeeded()
    await nextPage
    await page.waitForLoadState('networkidle')
    expect(offsets).toEqual(offset === 25 ? [0, 25] : [0, 25, 50])
  }
})
