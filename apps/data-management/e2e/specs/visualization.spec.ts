import { expect, test, type Page } from "../support/test";

import { authenticateSession } from "../support/auth";
import { fixtures, users } from "../support/fixtures";

test.describe("visualization", () => {
  function mobileDatastreamRow(page: Page, datastreamName: string) {
    return page.getByRole("row").filter({ hasText: datastreamName }).first();
  }

  async function ensureTableFiltersVisible(page: Page) {
    await expect(
      page.getByRole("button", { name: "Filter by workspace" }),
    ).toBeVisible();
  }

  async function plotPublicDatastream(page: Page) {
    await page
      .getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
      .click();
    await expect(
      page.getByTestId("clear-selected-datastreams"),
    ).toBeVisible();
  }

  test("visualization page renders filter controls and seeded datastream rows", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);
    await ensureTableFiltersVisible(page);

    await expect(
      page.getByRole("heading", { name: "Datastreams" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Filter by site" }),
    ).toBeVisible();
    await expect(
      page.getByTestId("clear-selected-datastreams"),
    ).toHaveCount(0);
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.publicSystemMetadata.name),
    ).toBeVisible();
  });

  test("visualization preserves selected datastream state in the URL and supports summary mode", async ({
    page,
    browser,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 });

    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    await expect(
      page.getByText(fixtures.datastreams.public.name, { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText(fixtures.datastreams.publicSystemMetadata.name, {
        exact: true,
      }),
    ).toBeVisible();

    await page
      .getByTestId(`datavis-metadata-${fixtures.datastreams.public.id}`)
      .click();
    await page.getByTestId("add-datastream-to-plot").click();
    await page.getByTestId("toggle-selected-datastreams").click();

    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.publicSystemMetadata.name),
    ).toHaveCount(0);

    await page.getByTestId("show-summary-view").click();
    await expect(
      page.getByText("Summary Statistics", { exact: true }),
    ).toBeVisible();

    await page.getByTestId("show-plot-view").click();

    // The visualization keeps all shareable state in the route query, so the
    // current URL is the "copied" link.
    await expect(page).toHaveURL(
      new RegExp(`datastreams=${fixtures.datastreams.public.id}`),
    );
    const copiedUrl = page.url();

    expect(copiedUrl).toContain(
      `/visualize-data?sites=${fixtures.monitoringSites.public.id}`,
    );
    expect(copiedUrl).toContain(
      `datastreams=${fixtures.datastreams.public.id}`,
    );

    const copiedContext = await browser.newContext();
    const copiedPage = await copiedContext.newPage();
    await copiedPage.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(
      copiedPage,
      users.owner.email,
      users.owner.password,
    );
    await copiedPage.goto(copiedUrl);

    await expect(
      copiedPage.getByTestId("clear-selected-datastreams"),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(copiedPage, fixtures.datastreams.public.name),
    ).toBeVisible();
    await copiedContext.close();
  });

  test("visualization header checkbox clears selected datastreams", async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    const tableHeader = page.locator("thead");
    const clearSelectedCheckbox = tableHeader.getByRole("checkbox", {
      name: "Clear selected datastreams",
    });

    await expect(clearSelectedCheckbox).toHaveCount(0);
    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`),
    ).toBeVisible();

    await plotPublicDatastream(page);
    await expect(clearSelectedCheckbox).toBeVisible();
    await expect(clearSelectedCheckbox).toHaveJSProperty("indeterminate", true);
    await expect(tableHeader).toContainText("1 of 5 selected");
    await page.getByTestId("toggle-selected-datastreams").click();

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`,
      ),
    ).toHaveCount(0);

    // clearSelected() resets showOnlySelected to false, so both rows are visible immediately
    await clearSelectedCheckbox.click();

    await expect(clearSelectedCheckbox).toHaveCount(0);
    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`,
      ),
    ).toBeVisible();
  });

  test("visualization filters can narrow datastreams by site", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto("/visualize-data");
    await ensureTableFiltersVisible(page);

    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(
        page,
        fixtures.datastreams.privateWorkspacePublic.name,
      ),
    ).toBeVisible();

    await page.getByRole("button", { name: "Filter by sites" }).click();
    await page
      .getByRole("checkbox", {
        name: `Sites: ${fixtures.monitoringSites.privateWorkspacePublic.name}`,
      })
      .click();
    // The filter menu stays open after a selection; dismiss it so its overlay
    // stops intercepting clicks on the search controls.
    await page.keyboard.press("Escape");

    const tableSearch = page.getByRole("combobox", { name: "Search" });
    const selectedSiteName = fixtures.monitoringSites.privateWorkspacePublic.name;
    const siteQualifier = /\s/.test(selectedSiteName)
      ? `site:"${selectedSiteName}"`
      : `site:${selectedSiteName}`;
    await expect(tableSearch).toHaveValue(siteQualifier);

    await expect(
      mobileDatastreamRow(
        page,
        fixtures.datastreams.privateWorkspacePublic.name,
      ),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toHaveCount(0);

    await page
      .getByRole("button", { name: "Clear search and filters" })
      .click();
    await expect(tableSearch).toHaveValue("");
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(
        page,
        fixtures.datastreams.privateWorkspacePublic.name,
      ),
    ).toBeVisible();

    await tableSearch.fill(siteQualifier);
    await expect(
      page.getByRole("button", { name: "Filter by sites (1 selected)" }),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(
        page,
        fixtures.datastreams.privateWorkspacePublic.name,
      ),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toHaveCount(0);
  });

  test("visualization search filters the mobile datastream cards", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    const tableSearch = page.getByRole("combobox", {
      name: "Search",
    });
    await expect(tableSearch).toBeVisible();

    await tableSearch.fill(fixtures.datastreams.publicSystemMetadata.name);
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.publicSystemMetadata.name),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toHaveCount(0);

    await tableSearch.clear();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toBeVisible();
  });

  test("visualization detail levels hide and restore row metadata", async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    const datastreamRow = page
      .getByRole("row")
      .filter({ hasText: fixtures.datastreams.public.name })
      .first();
    await expect(datastreamRow).toBeVisible();

    const signature = datastreamRow.locator(".datastream-signature");
    const observationRange = datastreamRow.locator(
      ".datastream-observation-range",
    );
    const moreDetail = page.getByTestId("show-more-datastream-details");
    const lessDetail = page.getByTestId("show-less-datastream-details");

    // Level 1 (default) shows only the datastream name.
    await expect(signature).toHaveCount(0);
    await expect(observationRange).toHaveCount(0);
    await expect(lessDetail).toBeDisabled();

    // Level 2 adds the processing-level / unit signature.
    await moreDetail.click();
    await expect(signature).toBeVisible();
    await expect(observationRange).toHaveCount(0);

    // Level 3 also adds the observation-range line.
    await moreDetail.click();
    await expect(observationRange).toBeVisible();
    await expect(moreDetail).toBeDisabled();

    // Stepping back down restores the earlier levels.
    await lessDetail.click();
    await expect(observationRange).toHaveCount(0);
    await expect(signature).toBeVisible();

    await lessDetail.click();
    await expect(signature).toHaveCount(0);
  });

  test("visualization quick-range date buttons update the time range", async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`),
    ).toBeVisible();

    await plotPublicDatastream(page);

    // Date preset chips use abbreviated labels: 1m, 6m, YTD, 1y, all
    await expect(page.getByText("1m").first()).toBeVisible();
    await expect(page.getByText("6m").first()).toBeVisible();
    await expect(page.getByText("1y").first()).toBeVisible();

    await page.getByText("1m").first().click();
    await page.getByText("6m").first().click();
    await page.getByText("1y").first().click();

    // Quick-range selection is mirrored into the route query.
    await expect(page).toHaveURL(/selectedDateBtnId=3/);
    const copiedUrl = new URL(page.url());

    expect(copiedUrl.searchParams.get("selectedDateBtnId")).toBe("3");
    expect(copiedUrl.searchParams.has("beginDate")).toBe(false);
    expect(copiedUrl.searchParams.has("endDate")).toBe(false);
    expect(copiedUrl.searchParams.has("xStart")).toBe(false);
    expect(copiedUrl.searchParams.has("xEnd")).toBe(false);
  });

  test("visualization custom date range can be set", async ({ page }) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`),
    ).toBeVisible();

    await plotPublicDatastream(page);

    // DatePickerField uses placeholder "Begin Date" / "End Date" and M/D/YYYY format
    const startDate = page.locator('input[placeholder="Begin Date"]').first();
    const endDate = page.locator('input[placeholder="End Date"]').first();

    await expect(startDate).toBeVisible();
    await expect(endDate).toBeVisible();

    await startDate.fill("1/1/2020");
    await endDate.fill("1/1/2021");
    await endDate.press("Tab");

    await expect(startDate).toHaveValue("1/1/2020");
    await expect(endDate).toHaveValue("1/1/2021");
  });

  test("visualization metadata modal supports plotting and downloads", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    await expect(
      page.getByTestId(`datavis-metadata-${fixtures.datastreams.public.id}`),
    ).toBeVisible();
    await page
      .getByTestId(`datavis-metadata-${fixtures.datastreams.public.id}`)
      .click();

    await expect(page.getByText("Datastream information")).toBeVisible();
    await expect(page.getByText("General", { exact: true })).toBeVisible();

    const csvDownload = page.waitForEvent("download");
    await page.getByTestId("download-datastream-csv").click();
    const csvArtifact = await csvDownload;
    expect(csvArtifact.suggestedFilename()).toBe(
      `datastream_${fixtures.datastreams.public.id}.csv`,
    );

    await page.getByTestId("add-datastream-to-plot").click();
    await page.getByTestId("toggle-selected-datastreams").click();

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`,
      ),
    ).toHaveCount(0);

    const zipDownload = page.waitForEvent("download");
    await page.getByTestId("download-selected-datastreams").click();
    const zipArtifact = await zipDownload;
    expect(zipArtifact.suggestedFilename()).toBe("datastreams.zip");
  });

  test("visualization metadata modal clear-and-plot resets the current selection", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    await page
      .getByTestId(`datavis-metadata-${fixtures.datastreams.public.id}`)
      .click();
    await page.getByTestId("add-datastream-to-plot").click();

    await page
      .getByTestId(
        `datavis-metadata-${fixtures.datastreams.publicSystemMetadata.id}`,
      )
      .click();
    await page.getByTestId("clear-and-plot-datastream").click();
    await page.getByTestId("toggle-selected-datastreams").click();

    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.publicSystemMetadata.name),
    ).toBeVisible();
    await expect(
      mobileDatastreamRow(page, fixtures.datastreams.public.name),
    ).toHaveCount(0);
  });

  test("visualization selected download works for multiple datastreams", async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    await page
      .getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
      .click();
    await page
      .getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`,
      )
      .click();

    const zipDownload = page.waitForEvent("download");
    await page.getByTestId("download-selected-datastreams").click();
    const zipArtifact = await zipDownload;
    expect(zipArtifact.suggestedFilename()).toBe("datastreams.zip");
  });
});
