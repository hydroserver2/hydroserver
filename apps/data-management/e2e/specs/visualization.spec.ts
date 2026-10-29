import { expect, test, type Page } from "../support/test";

import { authenticateSession } from "../support/auth";
import { fixtures, users } from "../support/fixtures";
import { readFile } from "node:fs/promises";
import { PlotlyColors } from "../../src/utils/materialColors";

test.describe("visualization", () => {
  test("image preview edits a zoomed snapshot and downloads an image without changing the page", async ({
    page,
  }, testInfo) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(
      `/visualize-data?datastreams=${fixtures.datastreams.public.id}`,
    );
    const live = page.locator(".plot-card .js-plotly-plot");
    await expect(live.locator(".legendtext")).toHaveCount(1);
    await expect(live.locator(".annotation-text")).toHaveCount(0);
    const originalLegend = await live.locator(".legendtext").textContent();
    const originalColor = await live.evaluate(
      (gd: any) => gd.data[0].line.color,
    );
    expect(await live.evaluate((gd: any) => gd.data[0].name)).not.toContain(
      "@ ",
    );
    await expect(
      page.getByRole("button", { name: "Show site name", exact: true }),
    ).toBeVisible();
    await live.locator('[data-title="Zoom"]').click();
    const dragArea = live.locator(".nsewdrag").first();
    await dragArea.scrollIntoViewIfNeeded();
    const box = (await dragArea.boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.25, box.y + box.height * 0.25);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.75, box.y + box.height * 0.75, {
      steps: 10,
    });
    await page.mouse.up();
    await expect(page).toHaveURL(/xStart=/);
    const url = page.url();
    const range = await live.evaluate((gd: any) => gd._fullLayout.xaxis.range);
    await page
      .getByRole("button", { name: "Show site name", exact: true })
      .click();
    await expect
      .poll(() => live.evaluate((gd: any) => gd.data[0].name))
      .toContain("@ ");
    expect(
      await live.evaluate((gd: any) => gd._fullLayout.xaxis.range),
    ).toEqual(range);
    await page
      .getByRole("button", { name: "Hide site name", exact: true })
      .click();
    await expect
      .poll(() => live.evaluate((gd: any) => gd.data[0].name))
      .not.toContain("@ ");
    expect(
      await live.evaluate((gd: any) => gd._fullLayout.xaxis.range),
    ).toEqual(range);
    await page
      .locator(".plot-toolbar")
      .screenshot({ path: testInfo.outputPath("screenshot-controls.png") });
    await live.locator('[data-title="Download plot image"]').click();
    const dialog = page.getByRole("dialog", { name: "Download plot image" });
    const figure = page.getByTestId("figure-plot");
    await expect(
      dialog.getByRole("button", { name: "Use blue for trace 1", exact: true }),
    ).toHaveCSS("background-color", "rgb(31, 119, 180)");
    await expect(figure.locator(".legendtext")).toHaveCount(1);
    await expect(figure.locator(".annotation-text")).toHaveCount(0);
    expect(await figure.evaluate((gd: any) => gd.data[0].name)).toContain("@ ");
    expect(
      await figure.evaluate((gd: any) => gd._fullLayout.xaxis.range),
    ).toEqual(range);
    await dialog
      .getByRole("textbox", { name: "Image title", exact: true })
      .fill("Logan River flow");
    await dialog
      .getByRole("textbox", { name: "Trace 1 name", exact: true })
      .fill("Upstream flow");
    await dialog
      .getByRole("button", { name: "Use red for trace 1", exact: true })
      .click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd.data[0].line.color))
      .toBe(PlotlyColors[3]);
    await dialog
      .getByLabel("Custom color for trace 1", { exact: true })
      .fill("#123456");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => [
          gd.data[0].line.color,
          gd.data[0].marker.color,
          gd._fullLayout.yaxis.title.font.color,
        ]),
      )
      .toEqual(["#123456", "#123456", "#123456"]);
    await dialog
      .getByRole("checkbox", { name: "Show site names", exact: true })
      .uncheck();
    await dialog
      .getByRole("textbox", { name: "X-axis label", exact: true })
      .fill("Time (UTC)");
    await dialog
      .getByRole("textbox", { name: "Y-axis label", exact: true })
      .fill("Discharge (m³ s⁻¹)");
    await expect(figure.locator(".legendtext")).toHaveText("Upstream flow");
    await expect(
      figure
        .locator(".annotation-text")
        .filter({ hasText: "Logan River flow" }),
    ).toHaveCount(1);
    await expect(figure.locator(".xtitle")).toHaveText("Time (UTC)");
    await expect(figure.locator(".ytitle")).toHaveText("Discharge (m³ s⁻¹)");
    await expect(
      dialog.getByRole("checkbox", { name: /site name for trace/i }),
    ).toHaveCount(0);
    await expect
      .poll(() => figure.evaluate((gd: any) => gd._fullLayout.legend.yanchor))
      .toBe("top");
    await dialog
      .getByRole("combobox", { name: "Legend position" })
      .press("ArrowDown");
    await page.getByRole("option", { name: "Above plot", exact: true }).click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd._fullLayout.legend.yanchor))
      .toBe("bottom");
    await dialog
      .getByRole("combobox", { name: "Legend position" })
      .press("ArrowDown");
    await page.getByRole("option", { name: "Below plot", exact: true }).click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd._fullLayout.legend.yanchor))
      .toBe("top");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => {
          const legend = gd.querySelector(".legend").getBoundingClientRect();
          const axis = gd.querySelector(".xtitle").getBoundingClientRect();
          const canvas = gd.getBoundingClientRect();
          return legend.top > axis.bottom && legend.bottom <= canvas.bottom;
        }),
      )
      .toBe(true);
    await dialog
      .getByRole("checkbox", { name: "Show legend", exact: true })
      .uncheck();
    await expect(figure.locator(".legend")).toHaveCount(0);
    await expect(
      dialog.getByRole("checkbox", { name: "Show site names", exact: true }),
    ).toHaveCount(0);
    await expect(
      dialog.getByRole("combobox", { name: "Legend position" }),
    ).toHaveCount(0);
    await dialog
      .getByRole("checkbox", { name: "Show legend", exact: true })
      .check();
    await expect(figure.locator(".legendtext")).toHaveText("Upstream flow");
    await expect(
      dialog.getByRole("checkbox", { name: "Show site names", exact: true }),
    ).not.toBeChecked();
    await expect(
      dialog.getByRole("combobox", { name: "Legend position" }),
    ).toHaveValue("Below plot");
    await page.screenshot({ path: testInfo.outputPath("figure-editor.png") });
    await expect(
      dialog.getByRole("complementary", { name: "Image settings" }),
    ).toHaveCount(1);
    await expect(
      dialog.getByRole("button", { name: "Download PNG", exact: true }),
    ).toHaveCount(1);
    await expect(figure.locator(".modebar")).toHaveCount(0);
    await figure.screenshot({
      path: testInfo.outputPath("figure-screenshot.png"),
    });
    const downloadPromise = page.waitForEvent("download");
    await dialog
      .getByRole("button", { name: "Download PNG", exact: true })
      .click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("Logan_River_flow.png");
    const imagePath = testInfo.outputPath("figure-export.png");
    await download.saveAs(imagePath);
    const png = await readFile(imagePath);
    expect(png.readUInt32BE(16)).toBeGreaterThanOrEqual(3840);
    await dialog.getByRole("button", { name: "Close image preview" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(url);
    await expect(live.locator(".legendtext")).toHaveText(originalLegend!);
    expect(await live.evaluate((gd: any) => gd.data[0].line.color)).toBe(
      originalColor,
    );
    expect(
      await live.evaluate((gd: any) => gd._fullLayout.xaxis.range),
    ).toEqual(range);
    await live.locator('[data-title="Download plot image"]').click();
    await expect(
      dialog.getByRole("textbox", { name: "Image title", exact: true }),
    ).toHaveValue("");
    await expect(
      dialog.getByLabel("Custom color for trace 1", { exact: true }),
    ).toHaveValue(originalColor);
    await dialog.getByRole("button", { name: "Close image preview" }).click();
  });

  test("image preview supports site-name controls, multiple axes and reset on narrow screens", async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: 500, height: 900 });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(
      `/visualize-data?datastreams=${fixtures.datastreams.public.id}&datastreams=${fixtures.datastreams.privateWorkspacePublic.id}&table=0`,
    );
    const live = page.locator(".plot-card .js-plotly-plot");
    await expect(live.locator(".legendtext")).toHaveCount(2);
    expect(
      await live.evaluate((gd: any) =>
        gd.data.every((trace: any) => !trace.name.includes("@ ")),
      ),
    ).toBe(true);
    await page
      .getByRole("button", { name: "Show site name", exact: true })
      .click();
    await expect
      .poll(() =>
        live.evaluate((gd: any) =>
          gd.data.every((trace: any) => trace.name.includes("@ ")),
        ),
      )
      .toBe(true);
    await live.locator('[data-title="Download plot image"]').click();
    const dialog = page.getByRole("dialog", { name: "Download plot image" });
    const figure = page.getByTestId("figure-plot");
    await dialog
      .getByRole("button", { name: "Use green for trace 1", exact: true })
      .click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd.data[0].line.color))
      .toBe(PlotlyColors[2]);
    await dialog
      .getByRole("group", { name: "Trace 1 color", exact: true })
      .getByRole("button", { name: "Reset color", exact: true })
      .click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd.data[0].line.color))
      .toBe(PlotlyColors[0]);
    await dialog
      .getByRole("button", { name: "Use green for trace 1", exact: true })
      .click();
    await expect(
      dialog.getByRole("textbox", { name: "Y-axis 2 label", exact: true }),
    ).toBeVisible();
    await dialog
      .getByRole("checkbox", { name: "Show site names", exact: true })
      .uncheck();
    await expect
      .poll(() =>
        figure.evaluate((gd: any) =>
          gd.data.every((trace: any) => !trace.name.includes("@")),
        ),
      )
      .toBe(true);
    await dialog
      .getByRole("checkbox", { name: "Show site names", exact: true })
      .check();
    await dialog
      .getByRole("textbox", { name: "Trace 1 site name", exact: true })
      .fill("Upper reach");
    await dialog
      .getByRole("textbox", { name: "Trace 1 name", exact: true })
      .fill("Temperature");
    await dialog
      .getByRole("textbox", { name: "Y-axis label", exact: true })
      .fill("Temperature (°C)");
    await dialog
      .getByRole("textbox", { name: "Y-axis 2 label", exact: true })
      .fill("Flow (m³/s)");
    await expect(figure.locator(".legendtext").first()).toContainText(
      "@ Upper reach",
    );
    await dialog
      .getByRole("combobox", { name: "Legend position" })
      .press("ArrowDown");
    await page.getByRole("option", { name: "Below plot", exact: true }).click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd._fullLayout.legend.yanchor))
      .toBe("top");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => {
          const legend = gd.querySelector(".legend").getBoundingClientRect();
          const axis = gd.querySelector(".xtitle").getBoundingClientRect();
          return (
            legend.top > axis.bottom &&
            legend.bottom <= gd.getBoundingClientRect().bottom
          );
        }),
      )
      .toBe(true);
    const bounds = await figure.boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(500);
    await figure.screenshot({ path: testInfo.outputPath("mobile-figure.png") });
    await dialog
      .getByRole("button", { name: "Reset image", exact: true })
      .click();
    await expect(
      dialog.getByRole("textbox", { name: "Trace 1 name", exact: true }),
    ).toHaveValue(fixtures.datastreams.public.name);
    await expect(
      dialog.getByLabel("Custom color for trace 1", { exact: true }),
    ).toHaveValue(PlotlyColors[0]);
    await expect(
      dialog.getByRole("checkbox", { name: "Show site names", exact: true }),
    ).toBeChecked();
    await expect(
      dialog.getByRole("checkbox", { name: "Show legend", exact: true }),
    ).toBeChecked();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd._fullLayout.legend.yanchor))
      .toBe("top");
    await dialog.getByRole("button", { name: "Close image preview" }).click();
    await expect(page).not.toHaveURL(/plotLabels=/);
    await expect(
      page.getByRole("button", { name: "Hide site name", exact: true }),
    ).toBeVisible();
    expect(
      await live.evaluate((gd: any) =>
        gd.data.every((trace: any) => trace.name.includes("@ ")),
      ),
    ).toBe(true);
  });

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

  test("visualization detail levels hide and restore observation metadata", async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?sites=${fixtures.monitoringSites.public.id}`);

    const datastreamRow = page
      .getByRole("row")
      .filter({ hasText: fixtures.datastreams.public.name })
      .first();
    await expect(datastreamRow).toBeVisible();

    const observationRange = datastreamRow.locator(
      ".datastream-observation-range",
    );
    const moreDetail = page.getByTestId("show-more-datastream-details");
    const lessDetail = page.getByTestId("show-less-datastream-details");

    // Level 1 (default) shows only the datastream name.
    await expect(observationRange).toHaveCount(0);
    await expect(lessDetail).toBeDisabled();

    // Level 2 adds the observation count and range.
    await moreDetail.click();
    await expect(observationRange).toBeVisible();
    await expect(moreDetail).toBeDisabled();

    // Stepping back down hides the observation count and range.
    await lessDetail.click();
    await expect(observationRange).toHaveCount(0);
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

    // Date preset chips use abbreviated labels: 1w, 1m, 6m, YTD, 1y, all
    await expect(page.getByText("1w").first()).toBeVisible();
    await expect(page.getByText("1m").first()).toBeVisible();
    await expect(page.getByText("6m").first()).toBeVisible();
    await expect(page.getByText("1y").first()).toBeVisible();

    await page.getByText("1w").first().click();
    await page.getByText("1m").first().click();
    await page.getByText("6m").first().click();
    await page.getByText("1y").first().click();

    // Quick-range selection is mirrored into the route query.
    await expect(page).toHaveURL(/selectedDateBtnId=4/);
    const copiedUrl = new URL(page.url());

    expect(copiedUrl.searchParams.get("selectedDateBtnId")).toBe("4");
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
