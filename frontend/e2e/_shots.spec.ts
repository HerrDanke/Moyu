import { test } from "@playwright/test";
import { importNovel, login } from "./helpers";

const OUT = "E:/FN_Syn/Github/Moyu/.bitfun/screens";

test("capture UI screenshots", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1280, height: 820 });
  await login(page);
  await importNovel(page, "shot");
  await page.reload();
  await page.waitForTimeout(1500);

  await page.screenshot({ path: `${OUT}/01-empty-light.png` });

  const input = page.locator('[data-testid="composer-input"]');
  await input.fill("下一章");
  await input.press("Enter");
  await page.waitForTimeout(7000);
  await page.screenshot({ path: `${OUT}/02-reading-light.png` });

  await page.locator('[data-testid="theme-toggle"]').click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/03-reading-dark.png` });

  await page.setViewportSize({ width: 390, height: 780 });
  await page.waitForTimeout(400);
  await page.locator('[data-testid="sidebar-toggle"]').click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/04-mobile-drawer-dark.png` });
});