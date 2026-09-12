import { expect, test } from "@playwright/test";
import { importNovel, login, openSettings, sendCommand } from "./helpers";

test.describe("ChatGPT 式外壳", () => {
  test("空状态：显示书名与进度，点示例指令即开始阅读", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "empty");

    // 导入后清一次会话，回到空状态
    await page.reload();
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="empty-state"]')).toContainText(/继续读《/);

    // 输入框在空状态时位于内容区中部（明显高于视口底部）
    const box = await page.locator(".composer").boundingBox();
    const viewport = page.viewportSize();
    expect(box).not.toBeNull();
    expect(viewport).not.toBeNull();
    if (box && viewport) {
      expect(box.y).toBeLessThan(viewport.height * 0.8);
    }

    // 点工具条的「下一章」→ 进入阅读 → 空状态消失、输入框落到底部
    await page.locator('[data-testid="toolbar-next"]').click();
    await expect(page.locator('[data-testid="empty-state"]')).toBeHidden({ timeout: 15_000 });
    await expect(page.locator('[data-testid="message-user"]')).toBeVisible({ timeout: 10_000 });

    await expect
      .poll(async () => {
        const b = await page.locator(".composer").boundingBox();
        return b ? b.y + b.height : 0;
      }, { timeout: 10_000, message: "发送后输入框应落到视口底部" })
      .toBeGreaterThan((viewport?.height ?? 0) * 0.7);
  });

  test("切书 = 新会话：清空消息并显示该书空状态", async ({ page }) => {
    test.setTimeout(90_000);
    await login(page);
    await importNovel(page, "bookA");
    await importNovel(page, "bookB");

    // 发一条消息，让当前书有会话内容
    await sendCommand(page, "下一章");
    await expect(page.locator('[data-testid="message-user"]')).toBeVisible({ timeout: 10_000 });

    // 找到非当前书的一本，点它
    const items = page.locator('[data-testid^="book-item-"]');
    const count = await items.count();
    expect(count).toBeGreaterThan(1);
    await items.first().click();

    // 消息清空 + 显示空状态
    await expect(page.locator('[data-testid="message-user"]')).toHaveCount(0, { timeout: 10_000 });
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible({ timeout: 10_000 });
  });

  test("窄屏：侧栏折叠为抽屉，可开合、Esc 关闭", async ({ page }) => {
    test.setTimeout(60_000);
    await page.setViewportSize({ width: 390, height: 760 });
    await login(page);

    const toggle = page.locator('[data-testid="sidebar-toggle"]');
    await expect(toggle).toBeVisible();

    await toggle.click();
    await expect(page.locator('[data-testid="sidebar"]')).toHaveClass(/is-open/);

    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="sidebar"]')).not.toHaveClass(/is-open/);
  });

  test("深色主题：切换后刷新仍保持", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);

    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await openSettings(page);
    await page.locator('[data-testid="theme-toggle"]').click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("阅读宽度：切到紧凑后刷新仍保持", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);

    await expect(page.locator("html")).toHaveAttribute("data-reading", "wide");
    await openSettings(page);
    await page.locator('[data-testid="reading-mode-toggle"]').click();
    await expect(page.locator("html")).toHaveAttribute("data-reading", "compact");

    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-reading", "compact");
  });

  test("助手正文不带气泡、用户消息是气泡", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "bubble");

    await sendCommand(page, "下一章");

    await expect(page.locator('[data-testid="message-user"]')).toBeVisible({ timeout: 10_000 });
    // 用户消息有背景色
    const userBg = await page
      .locator('[data-testid="message-user"] .bubble')
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    // 助手区域内不存在气泡元素
    await expect(page.locator('[data-testid="message-assistant"] .bubble')).toHaveCount(0);
    const assistantBg = await page
      .locator('[data-testid="message-assistant"] .assistant-body')
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(userBg).not.toBe(assistantBg);
  });
});