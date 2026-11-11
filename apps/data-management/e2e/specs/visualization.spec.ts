import { expect, test, type Page } from "../support/test";

import { authenticateSession } from "../support/auth";
import { fixtures, users } from "../support/fixtures";
import { readFile } from "node:fs/promises";
import { PlotlyColors } from "../../src/utils/materialColors";

test.describe("visualization", () => {
  test("image export supports screen resolution and print size with embedded DPI", async ({
    page,
  }, testInfo) => {
    test.setTimeout(120000);
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(
      `/visualize-data?datastreams=${fixtures.datastreams.public.id}`
    );
    const live = page.locator(".plot-card .js-plotly-plot");
    await expect(live.locator(".legendtext")).toHaveCount(1);
    await live.locator('[data-title="Download plot image"]').click();
    const dialog = page.getByRole("dialog", { name: "Download plot image" });
    const editor = dialog.getByRole("complementary", { name: "Image settings" });
    const figure = page.getByTestId("figure-plot");
    const summary = editor.locator(".figure-export-summary");
    const downloadButton = dialog.getByRole("button", {
      name: "Download PNG",
      exact: true,
    });
    const screen = editor.getByRole("button", { name: "Screen", exact: true });
    const print = editor.getByRole("button", { name: "Print", exact: true });
    await expect(screen).toHaveAttribute("aria-pressed", "true");
    expect(Number(await editor.getByRole("spinbutton", { name: "Width", exact: true }).getAttribute("max"))).toBeGreaterThan(6000);
    await editor.getByRole("combobox", { name: "Resolution" }).press("ArrowDown");
    await page.getByRole("option", { name: "High · 2×", exact: true }).click();
    await expect(summary).toContainText("2400 × 1800 px");
    const screenDownload = page.waitForEvent("download");
    await downloadButton.click();
    const screenPath = testInfo.outputPath("screen-2x.png");
    await (await screenDownload).saveAs(screenPath);
    const screenPng = await readFile(screenPath);
    expect([screenPng.readUInt32BE(16), screenPng.readUInt32BE(20)]).toEqual([
      2400, 1800,
    ]);

    await print.click();
    await expect(print).toHaveAttribute("aria-pressed", "true");
    await expect(summary).toContainText("1800 × 1350 px");
    await expect(summary).toContainText("6 × 4.5 in · 300 DPI");
    await expect(
      editor.getByRole("combobox", { name: "Resolution" })
    ).toHaveCount(0);
    await editor
      .getByRole("combobox", { name: "Units", exact: true })
      .press("ArrowDown");
    await page.getByRole("option", { name: "cm", exact: true }).click();
    const width = editor.getByRole("spinbutton", {
      name: "Print width",
      exact: true,
    });
    await expect(width).toHaveValue("15.24");
    await expect(summary).toContainText("1800 × 1350 px");
    const height = editor.getByRole("spinbutton", {
      name: "Print height", exact: true,
    });
    await expect(height).toHaveValue("11.43");
    await height.fill("");
    await expect(height).toHaveValue("");
    await expect(downloadButton).toBeDisabled();
    await height.fill("0");
    await expect(downloadButton).toBeDisabled();
    await height.fill("10");
    await expect(width).toHaveValue("15.24");
    await expect(summary).toContainText("1800 × 1181 px");
    await expect(
      editor.getByRole("combobox", { name: "Print size", exact: true })
    ).toHaveValue("Custom");
    await width.fill("");
    await expect(downloadButton).toBeDisabled();
    await expect(width).toHaveValue("");
    await width.fill("15.24");
    await editor
      .getByRole("combobox", { name: "Print quality", exact: true })
      .press("ArrowDown");
    await page.getByRole("option", { name: "Custom DPI", exact: true }).click();
    const dpi = editor.getByRole("spinbutton", {
      name: "Custom DPI",
      exact: true,
    });
    await dpi.fill("600");
    await expect(summary).toContainText("3600 × 2362 px");
    await expect
      .poll(() => figure.evaluate((gd: any) => gd._context.plotGlPixelRatio))
      .toBe(3);
    await dpi.fill("0");
    await expect(downloadButton).toBeDisabled();
    await dpi.fill("1200");
    await expect(downloadButton).toBeEnabled();
    await expect(summary).toContainText("7200 × 4724 px");
    const maximumDpi = Number(await dpi.getAttribute("max"));
    expect(maximumDpi).toBeGreaterThan(1200);
    await dpi.fill(String(maximumDpi + 1));
    await expect(downloadButton).toBeDisabled();
    await dpi.fill("300");
    await expect(downloadButton).toBeEnabled();
    await editor
      .getByRole("combobox", { name: "Print quality", exact: true })
      .press("ArrowDown");
    await page
      .getByRole("option", { name: "Standard · 300 DPI", exact: true })
      .click();
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => [
          gd._fullLayout.width,
          gd._fullLayout.font.size,
        ])
      )
      .toEqual([1200, 24]);
    expect(await figure.evaluate((gd: any) => gd._fullLayout.height)).toBeCloseTo(1181 / 1.5);
    await expect(page.getByRole("listbox")).toBeHidden();
    await page.screenshot({
      path: testInfo.outputPath("print-quality-settings.png"),
    });
    const printDownload = page.waitForEvent("download");
    await downloadButton.click();
    const printPath = testInfo.outputPath("print-300dpi.png");
    await (await printDownload).saveAs(printPath);
    const printPng = await readFile(printPath);
    expect([printPng.readUInt32BE(16), printPng.readUInt32BE(20)]).toEqual([
      1800, 1181,
    ]);
    const resolutions: number[] = [];
    for (let offset = 8; offset < printPng.length;) {
      const length = printPng.readUInt32BE(offset);
      if (printPng.toString("ascii", offset + 4, offset + 8) === "pHYs") {
        resolutions.push(printPng.readUInt32BE(offset + 8) * 0.0254);
        expect(printPng.readUInt32BE(offset + 8)).toBe(
          printPng.readUInt32BE(offset + 12)
        );
        expect(printPng[offset + 16]).toBe(1);
      }
      offset += length + 12;
    }
    expect(resolutions).toHaveLength(1);
    expect(resolutions[0]).toBeCloseTo(300, 1);
    await screen.click();
    await expect(summary).toContainText("2400 × 1800 px");
    await expect(
      editor.getByRole("spinbutton", { name: "Width", exact: true })
    ).toHaveValue("1200");
    await expect(
      editor.getByRole("spinbutton", { name: "Height", exact: true })
    ).toHaveValue("900");
    await print.click();
    await expect(height).toHaveValue("10");
    await expect(width).toHaveValue("15.24");
    const printSize = editor.getByRole("combobox", { name: "Print size", exact: true });
    await expect(editor.getByRole("combobox", { name: "Image shape", exact: true })).toHaveCount(0);
    const sizeExpectations = [
      { name: "3.5 × 2.5 in", width: "8.89", height: "6.35", pixels: "1050 × 750 px" },
      { name: "7 × 3.5 in", width: "17.78", height: "8.89", pixels: "2100 × 1050 px" },
      { name: "6 × 4 in", width: "15.24", height: "10.16", pixels: "1800 × 1200 px" },
      { name: "4 × 6 in", width: "10.16", height: "15.24", pixels: "1200 × 1800 px" },
      { name: "5 × 5 in", width: "12.7", height: "12.7", pixels: "1500 × 1500 px" },
      { name: "7 × 5 in", width: "17.78", height: "12.7", pixels: "2100 × 1500 px" },
      { name: "5 × 7 in", width: "12.7", height: "17.78", pixels: "1500 × 2100 px" },
      { name: "8 × 10 in", width: "20.32", height: "25.4", pixels: "2400 × 3000 px" },
      { name: "8.5 × 11 in", width: "21.59", height: "27.94", pixels: "2550 × 3300 px" },
    ];
    for (const size of sizeExpectations) {
      await printSize.press("ArrowDown");
      await page.getByRole("option", { name: size.name, exact: true }).click();
      await expect(width).toHaveValue(size.width);
      await expect(height).toHaveValue(size.height);
      await expect(summary).toContainText(size.pixels);
      await expect(downloadButton).toBeEnabled();
    }
    await editor.getByRole("combobox", { name: "Units", exact: true }).press("ArrowDown");
    await page.getByRole("option", { name: "Inches", exact: true }).click();
    await expect(width).toHaveValue("8.5");
    await expect(height).toHaveValue("11");
    await expect(printSize).toHaveValue("8.5 × 11 in");
    await printSize.press("ArrowDown");
    await page.getByRole("option", { name: "6 × 4 in", exact: true }).click();
    const quality = editor.getByRole("combobox", { name: "Print quality", exact: true });
    for (const level of [
      { name: "Mixed artwork · 500 DPI", pixels: "3000 × 2000 px" },
      { name: "Line art · 1000 DPI", pixels: "6000 × 4000 px" },
      { name: "Fine line art · 1200 DPI", pixels: "7200 × 4800 px" },
    ]) {
      await quality.press("ArrowDown");
      await page.getByRole("option", { name: level.name, exact: true }).click();
      await expect(summary).toContainText(level.pixels);
      await expect(downloadButton).toBeEnabled();
    }
    // Every offered size also renders at the highest preset quality on desktop.
    for (const size of sizeExpectations) {
      await printSize.press("ArrowDown");
      await page.getByRole("option", { name: size.name, exact: true }).click();
      await expect(downloadButton).toBeEnabled();
    }
    await printSize.press("ArrowDown");
    await page.getByRole("option", { name: "6 × 4 in", exact: true }).click();
    const lineArtDownload = page.waitForEvent("download");
    await downloadButton.click();
    const lineArtPath = testInfo.outputPath("hydrograph-1200dpi.png");
    await (await lineArtDownload).saveAs(lineArtPath);
    const lineArtPng = await readFile(lineArtPath);
    expect([lineArtPng.readUInt32BE(16), lineArtPng.readUInt32BE(20)]).toEqual([7200, 4800]);
    const resolutionOffset = lineArtPng.indexOf("pHYs");
    expect(resolutionOffset).toBeGreaterThan(0);
    expect(lineArtPng.readUInt32BE(resolutionOffset + 4) * 0.0254).toBeCloseTo(1200, 1);
    await printSize.press("ArrowDown");
    await page.getByRole("option", { name: "8.5 × 11 in", exact: true }).click();
    const largestDownload = page.waitForEvent("download");
    await downloadButton.click();
    const largestPath = testInfo.outputPath("letter-1200dpi.png");
    await (await largestDownload).saveAs(largestPath);
    const largestPng = await readFile(largestPath);
    expect([largestPng.readUInt32BE(16), largestPng.readUInt32BE(20)]).toEqual([10200, 13200]);
    await printSize.press("ArrowDown");
    await page.getByRole("option", { name: "6 × 4 in", exact: true }).click();
    await height.fill("2");
    await expect(printSize).toHaveValue("Custom");
    await expect(summary).toContainText("7200 × 2400 px");
    await screen.click();
    await expect(editor.getByRole("combobox", { name: "Print size", exact: true })).toHaveCount(0);
    await editor.getByRole("combobox", { name: "Image shape", exact: true }).press("ArrowDown");
    await expect(page.getByRole("option", { name: "Widescreen (16:9)", exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await dialog
      .getByRole("button", { name: "Reset image", exact: true })
      .click();
    await expect(screen).toHaveAttribute("aria-pressed", "true");
    await expect(summary).toContainText("1200 × 900 px");
  });

  test("image export menus omit sizes and quality levels beyond browser limits", async ({ page }) => {
    await page.addInitScript(() => {
      const original = CanvasRenderingContext2D.prototype.getImageData;
      CanvasRenderingContext2D.prototype.getImageData = function (
        sx: number, sy: number, sw: number, sh: number, settings?: ImageDataSettings
      ) {
        if (this.canvas.width > 4096 || this.canvas.height > 4096)
          throw new Error("Simulated canvas dimension limit");
        return original.call(this, sx, sy, sw, sh, settings);
      };
    });
    await authenticateSession(page, users.owner.email, users.owner.password);
    await page.goto(`/visualize-data?datastreams=${fixtures.datastreams.public.id}`);
    const live = page.locator(".plot-card .js-plotly-plot");
    await expect(live.locator(".legendtext")).toHaveCount(1);
    await live.locator('[data-title="Download plot image"]').click();
    const dialog = page.getByRole("dialog", { name: "Download plot image" });
    const editor = dialog.getByRole("complementary", { name: "Image settings" });
    await editor.getByRole("button", { name: "Print", exact: true }).click();
    const quality = editor.getByRole("combobox", { name: "Print quality", exact: true });
    await quality.press("ArrowDown");
    await expect(page.getByRole("option", { name: "Fine line art · 1200 DPI", exact: true })).toHaveCount(0);
    await page.getByRole("option", { name: "Fine detail · 600 DPI", exact: true }).click();
    const size = editor.getByRole("combobox", { name: "Print size", exact: true });
    await size.press("ArrowDown");
    await expect(page.getByRole("option", { name: "8.5 × 11 in", exact: true })).toHaveCount(0);
    await expect(page.getByRole("option", { name: "8 × 10 in", exact: true })).toHaveCount(0);
    await page.getByRole("option", { name: "6 × 4 in", exact: true }).click();
    await expect(dialog.getByRole("button", { name: "Download PNG", exact: true })).toBeEnabled();
    await quality.press("ArrowDown");
    await page.getByRole("option", { name: "Standard · 300 DPI", exact: true }).click();
    await size.press("ArrowDown");
    await page.getByRole("option", { name: "8.5 × 11 in", exact: true }).click();
    await quality.press("ArrowDown");
    await expect(page.getByRole("option", { name: "Fine detail · 600 DPI", exact: true })).toHaveCount(0);
    await expect(page.getByRole("option", { name: "Mixed artwork · 500 DPI", exact: true })).toHaveCount(0);
    await page.getByRole("option", { name: "Custom DPI", exact: true }).click();
    const dpi = editor.getByRole("spinbutton", { name: "Custom DPI", exact: true });
    await expect(dpi).toHaveAttribute("max", "372");
    await dpi.fill("373");
    await expect(dialog.getByRole("button", { name: "Download PNG", exact: true })).toBeDisabled();
    await expect(editor.getByText(/This DPI exceeds your browser’s export limits/)).toHaveCount(1);
    await dpi.fill("372");
    await expect(dialog.getByRole("button", { name: "Download PNG", exact: true })).toBeEnabled();
  });

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
      dialog
        .getByRole("button", { name: "Choose color for trace 1", exact: true })
        .locator(".figure-current-color"),
    ).toHaveCSS("background-color", "rgb(31, 119, 180)");
    await expect(figure.locator(".legendtext")).toHaveCount(1);
    await expect(figure.locator(".annotation-text")).toHaveCount(0);
    expect(await figure.evaluate((gd: any) => gd.data[0].name)).toContain("@ ");
    expect(
      await figure.evaluate((gd: any) => gd._fullLayout.xaxis.range),
    ).toEqual(range);
    const textSize = dialog.getByRole("spinbutton", { name: "Text size", exact: true });
    await expect(textSize).toHaveAttribute("type", "number");
    await expect(textSize).toHaveValue("24");
    await textSize.press("ArrowUp");
    await expect(textSize).toHaveValue("25");
    await textSize.press("ArrowDown");
    await expect(textSize).toHaveValue("24");
    await textSize.fill("27.5");
    await textSize.press("Tab");
    await expect.poll(() => figure.evaluate((gd: any) => gd._fullLayout.font.size)).toBe(27.5);
    await dialog.getByRole("button", { name: "Print", exact: true }).click();
    await expect(textSize).toHaveValue("27.5");
    await textSize.press("ArrowUp");
    await expect(textSize).toHaveValue("28");
    await expect.poll(() => figure.evaluate((gd: any) => gd._fullLayout.font.size)).toBe(28);
    await textSize.fill("");
    await expect(dialog.getByRole("button", { name: "Download PNG", exact: true })).toBeDisabled();
    await textSize.fill("24");
    await textSize.press("Tab");
    await expect.poll(() => figure.evaluate((gd: any) => gd._fullLayout.font.size)).toBe(24);
    await dialog.getByRole("button", { name: "Screen", exact: true }).click();
    const widthField = dialog.getByRole("spinbutton", {
      name: "Width",
      exact: true,
    });
    const heightField = dialog.getByRole("spinbutton", {
      name: "Height",
      exact: true,
    });
    await expect(widthField).toHaveValue("1200");
    await expect(heightField).toHaveValue("900");
    await dialog
      .getByRole("combobox", { name: "Image shape", exact: true })
      .press("ArrowDown");
    await page.getByRole("option", { name: "Custom", exact: true }).click();
    await expect(
      dialog.getByRole("combobox", { name: "Image shape", exact: true }),
    ).toHaveValue("Custom");
    await expect(widthField).toHaveValue("1200");
    await expect(heightField).toHaveValue("900");
    await widthField.fill("2400");
    await heightField.fill("1800");
    await expect(
      dialog.getByRole("combobox", { name: "Image shape", exact: true }),
    ).toHaveValue("Custom");
    await dialog
      .getByRole("combobox", { name: "Image shape", exact: true })
      .press("ArrowDown");
    await page
      .getByRole("option", { name: "Square (1:1)", exact: true })
      .click();
    await expect(widthField).toHaveValue("1200");
    await expect(heightField).toHaveValue("1200");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => [
          gd._fullLayout.width,
          gd._fullLayout.height,
        ]),
      )
      .toEqual([1200, 1200]);
    await widthField.fill("");
    await expect(
      dialog.getByRole("button", { name: "Download PNG", exact: true }),
    ).toBeDisabled();
    await widthField.fill("400");
    await heightField.fill("300");
    await expect(
      dialog.getByRole("combobox", { name: "Image shape", exact: true }),
    ).toHaveValue("Custom");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => [
          gd._fullLayout.width,
          gd._fullLayout.height,
        ]),
      )
      .toEqual([400, 300]);
    await widthField.fill("1000");
    await heightField.fill("700");
    await expect(
      dialog.getByRole("combobox", { name: "Image shape", exact: true }),
    ).toHaveValue("Custom");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => [
          gd._fullLayout.width,
          gd._fullLayout.height,
        ]),
      )
      .toEqual([1000, 700]);
    await page.screenshot({
      path: testInfo.outputPath("image-dimensions.png"),
    });
    await dialog
      .getByRole("textbox", { name: "Image title", exact: true })
      .fill("Logan River flow");
    await dialog
      .getByRole("textbox", { name: "Trace 1 name", exact: true })
      .fill("Upstream flow");
    await dialog
      .getByRole("button", { name: "Choose color for trace 1", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Use red for trace 1", exact: true })
      .click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd.data[0].line.color))
      .toBe(PlotlyColors[3]);
    const colorPopup = page.getByRole("group", {
      name: "Trace 1 color picker",
      exact: true,
    });
    const paletteBounds = await colorPopup
      .getByRole("button", { name: "Use red for trace 1", exact: true })
      .boundingBox();
    const canvasBounds = await colorPopup.locator("canvas").boundingBox();
    expect(paletteBounds!.y + paletteBounds!.height).toBeLessThanOrEqual(
      canvasBounds!.y,
    );
    await colorPopup
      .getByRole("textbox", { name: "HEX value", exact: true })
      .fill("#123456");
    await colorPopup
      .getByRole("textbox", { name: "HEX value", exact: true })
      .press("Tab");
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => gd.data[0].line.color.toLowerCase()),
      )
      .toBe("#123456");
    await page.screenshot({
      path: testInfo.outputPath("color-picker-desktop.png"),
    });
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Use red for trace 1", exact: true }),
    ).not.toBeVisible();
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
    await expect
      .poll(() =>
        figure.evaluate((gd: any) => {
          const title = gd.querySelector(".annotation-text");
          const axis = gd.querySelector(".xtitle");
          const titleBounds = title.getBoundingClientRect();
          const axisBounds = axis.getBoundingClientRect();
          return (
            Math.abs(
              titleBounds.x +
                titleBounds.width / 2 -
                axisBounds.x -
                axisBounds.width / 2,
            ) < 1 &&
            getComputedStyle(title).fontSize === getComputedStyle(axis).fontSize
          );
        }),
      )
      .toBe(true);
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
      .poll(() =>
        figure.evaluate((gd: any) => {
          const legend = gd.querySelector(".legend").getBoundingClientRect();
          const title = gd
            .querySelector(".annotation-text")
            .getBoundingClientRect();
          return legend.bottom <= title.top;
        }),
      )
      .toBe(true);
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
    expect(png.readUInt32BE(16)).toBe(1000);
    expect(png.readUInt32BE(20)).toBe(700);
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
      dialog.getByRole("button", {
        name: "Choose color for trace 1",
        exact: true,
      }),
    ).toContainText(originalColor);
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
      .getByRole("button", { name: "Choose color for trace 1", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Use green for trace 1", exact: true })
      .click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd.data[0].line.color))
      .toBe(PlotlyColors[2]);
    const popupBounds = await page
      .getByRole("group", { name: "Trace 1 color picker", exact: true })
      .boundingBox();
    expect(popupBounds!.x).toBeGreaterThanOrEqual(0);
    expect(popupBounds!.x + popupBounds!.width).toBeLessThanOrEqual(500);
    await page.screenshot({
      path: testInfo.outputPath("color-picker-mobile.png"),
    });
    await page.keyboard.press("Escape");
    await dialog
      .getByRole("group", { name: "Trace 1 color", exact: true })
      .getByRole("button", { name: "Reset color", exact: true })
      .click();
    await expect
      .poll(() => figure.evaluate((gd: any) => gd.data[0].line.color))
      .toBe(PlotlyColors[0]);
    await dialog
      .getByRole("button", { name: "Choose color for trace 1", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Use green for trace 1", exact: true })
      .click();
    await page.keyboard.press("Escape");
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
      dialog.getByRole("button", {
        name: "Choose color for trace 1",
        exact: true,
      }),
    ).toContainText(PlotlyColors[0]);
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
