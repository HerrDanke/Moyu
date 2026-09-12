import { test } from "@playwright/test";
import { importNovel, login } from "./helpers";

test("probe paragraph rendering", async ({ page }) => {
  test.setTimeout(90_000);
  await login(page);
  await importNovel(page, "probe");
  await page.reload();
  await page.waitForTimeout(1000);

  const input = page.locator('[data-testid="composer-input"]');
  await input.fill("下一章");
  await input.press("Enter");
  await page.waitForTimeout(8000);

  const info = await page.evaluate(() => {
    const assistant = document.querySelector('[data-testid="message-assistant"]');
    const paras = assistant?.querySelectorAll(".chapter-text .para") ?? [];
    return {
      paraCount: paras.length,
      texts: Array.from(paras).map((p) => (p.textContent ?? "").slice(0, 40)),
      rawHtml: (assistant?.querySelector(".chapter-text")?.innerHTML ?? "").slice(0, 400),
    };
  });
  console.log("PARA_COUNT => " + info.paraCount);
  console.log("TEXTS => " + JSON.stringify(info.texts, null, 1));
  console.log("HTML => " + info.rawHtml);
});