import { expect, test } from "@playwright/test";
import {
  importPacedNovel,
  measureStreamMs,
  openSettings,
  login,
  setThinkingLevel,
} from "./helpers";

test.describe("设置面板与思考强度", () => {
  test("侧栏已精简，四个开关移入设置面板", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);

    // 侧栏底部不再直接暴露这些开关
    for (const id of ["theme-toggle", "reading-mode-toggle", "quick-read-toggle", "logout-button"]) {
      await expect(page.locator(`[data-testid="sidebar"] [data-testid="${id}"]`)).toHaveCount(0);
    }
    // 但仍保留 设置 / 用户管理 / 用户区
    await expect(page.locator('[data-testid="settings-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-admin-entry"]')).toBeVisible();
    await expect(page.locator('[data-testid="sidebar-user"]')).toBeVisible();

    await openSettings(page);
    for (const id of ["theme-toggle", "reading-mode-toggle", "quick-read-toggle", "logout-button"]) {
      await expect(page.locator(`[data-testid="settings-dialog"] [data-testid="${id}"]`)).toBeVisible();
    }
  });

  test("打开与关闭：Esc 关闭且焦点回到设置按钮", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);

    await page.locator('[data-testid="settings-button"]').click();
    const dialog = page.locator('[data-testid="settings-dialog"]');
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(page.locator('[data-testid="settings-button"]')).toBeFocused();
  });

  test("思考强度有五个档位（含更快的「极速」）", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await openSettings(page);

    const slider = page.locator('[data-testid="thinking-slider"]');
    await expect(slider).toHaveAttribute("min", "1");
    await expect(slider).toHaveAttribute("max", "5");
    for (const name of ["极速", "迅捷", "标准", "深入", "沉思"]) {
      await expect(page.locator(".slider-ticks")).toContainText(name);
    }
  });

  test("思考强度按用户保存：刷新后仍保持", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);

    await setThinkingLevel(page, 4);
    await expect
      .poll(async () => {
        await page.locator('[data-testid="settings-button"]').click();
        const t = (await page.locator('[data-testid="thinking-label"]').textContent()) ?? "";
        await page.keyboard.press("Escape");
        return t;
      })
      .toBe("深入");

    await page.reload();
    await openSettings(page);
    await expect(page.locator('[data-testid="thinking-label"]')).toHaveText("深入");
  });

  test("思考强度真的改变出字节奏（沉思 明显慢于 极速）", async ({ page }) => {
    test.setTimeout(180_000);
    await login(page);
    await importPacedNovel(page, "pace");

    await setThinkingLevel(page, 1);
    const fast = await measureStreamMs(page, "第 1 章");

    await setThinkingLevel(page, 5);
    const slow = await measureStreamMs(page, "第 2 章");

    console.log(`极速=${fast}ms 沉思=${slow}ms`);
    expect(slow).toBeGreaterThan(fast * 1.8);
  });
});