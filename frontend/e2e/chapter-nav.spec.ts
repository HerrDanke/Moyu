import { expect, test, type Page } from "@playwright/test";
import { importGeneratedNovel, importNovel, login } from "./helpers";

async function sendVia(page: Page, testId: string) {
  await page.locator(`[data-testid="${testId}"]`).click();
}

test.describe("阅读快捷工具条与章节目录", () => {
  test("工具条四个按钮齐备", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "toolbar");

    const bar = page.locator('[data-testid="reading-toolbar"]');
    await expect(bar).toBeVisible();
    for (const id of ["toolbar-prev", "toolbar-next", "toolbar-toc", "toolbar-jump"]) {
      await expect(page.locator(`[data-testid="${id}"]`)).toBeVisible();
    }
  });

  test("点「下一章」即可阅读（等价于手输指令）", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "toolnext");

    await sendVia(page, "toolbar-next");
    await expect(page.locator('[data-testid="message-user"]')).toContainText("下一章");
    await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 30_000 });
  });

  test("生成中禁用发送类按钮，但目录与跳转仍可用", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "tooldisabled");

    await sendVia(page, "toolbar-next");
    await expect(page.locator('[data-testid="toolbar-next"]')).toBeDisabled();
    await expect(page.locator('[data-testid="toolbar-prev"]')).toBeDisabled();
    await expect(page.locator('[data-testid="toolbar-toc"]')).toBeEnabled();
    await expect(page.locator('[data-testid="toolbar-jump"]')).toBeEnabled();

    await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('[data-testid="toolbar-next"]')).toBeEnabled();
  });

  test("点「跳转章节」预填输入框，且不发请求", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "tooljump");

    const chatCalls: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/api/chat")) chatCalls.push(r.url());
    });

    await sendVia(page, "toolbar-jump");
    const input = page.locator('[data-testid="composer-input"]');
    await expect(input).toHaveValue("第 ");
    await expect(input).toBeFocused();
    expect(chatCalls.length).toBe(0);

    // 补全数字并回车 → 真的跳章
    await input.fill("第 2 章");
    await input.press("Enter");
    await expect(page.locator('[data-testid="message-user"]')).toContainText("第 2 章");
    await expect(page.getByText(/第 2 章完/)).toBeVisible({ timeout: 30_000 });
  });

  test("空状态不再出现与工具条重复的按钮", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "emptychips");
    await page.reload();

    const empty = page.locator('[data-testid="empty-state"]');
    await expect(empty).toBeVisible({ timeout: 10_000 });
    await expect(empty).toContainText(/继续读《/);
    // 空状态内不应再有可点按钮
    await expect(empty.locator("button")).toHaveCount(0);
  });

  test("目录：打开、定位当前章、点章跳转", async ({ page }) => {
    test.setTimeout(90_000);
    await login(page);
    await importGeneratedNovel(page, 40, "toc");

    // 先读到第 3 章，验证打开目录时高亮当前章
    const input = page.locator('[data-testid="composer-input"]');
    await input.fill("第 3 章");
    await input.press("Enter");
    await expect(page.getByText(/第 3 章完/)).toBeVisible({ timeout: 30_000 });

    await sendVia(page, "toolbar-toc");
    const drawer = page.locator('[data-testid="toc-drawer"]');
    await expect(drawer).toBeVisible();
    await expect(drawer.locator('[data-testid="toc-item-3"]')).toHaveAttribute(
      "aria-current",
      "true",
    );

    // 点第 7 章
    await drawer.locator('[data-testid="toc-item-7"]').click();
    await expect(drawer).toBeHidden();
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText("第 7 章");
    await expect(page.getByText(/第 7 章完/)).toBeVisible({ timeout: 30_000 });

    // Esc 关闭且焦点回到「目录」按钮
    await sendVia(page, "toolbar-toc");
    await expect(drawer).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
    await expect(page.locator('[data-testid="toolbar-toc"]')).toBeFocused();
  });

  test("目录搜索：过滤后点击跳转的是真实章号", async ({ page }) => {
    test.setTimeout(90_000);
    await login(page);
    await importGeneratedNovel(page, 40, "tocsearch");

    await sendVia(page, "toolbar-toc");
    const drawer = page.locator('[data-testid="toc-drawer"]');
    await expect(drawer).toBeVisible();

    await drawer.locator('[data-testid="toc-search"]').fill("标题8");
    // 只剩标题8（以及标题18/28/38 也会命中「标题8」子串）
    await expect(drawer.locator('[data-testid="toc-item-8"]')).toBeVisible();
    await expect(drawer.locator('[data-testid="toc-item-7"]')).toHaveCount(0);

    await drawer.locator('[data-testid="toc-item-18"]').click();
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText("第 18 章");
  });

  test("目录窗口化：300 章只渲染可视区域的行", async ({ page }) => {
    test.setTimeout(150_000);
    await login(page);
    await importGeneratedNovel(page, 300, "tocwindow");

    await sendVia(page, "toolbar-toc");
    const drawer = page.locator('[data-testid="toc-drawer"]');
    await expect(drawer).toBeVisible();
    await expect(drawer.locator('[data-testid="toc-item-1"]')).toBeVisible();

    const rendered = await drawer.locator('[data-testid^="toc-item-"]').count();
    // 窗口化生效：远少于 300
    expect(rendered).toBeLessThan(120);
    expect(rendered).toBeGreaterThan(0);

    // 滚动到底部仍能正确落到末章（说明索引映射没坏）
    await drawer.locator(".drawer-list").evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });
    await expect(drawer.locator('[data-testid="toc-item-300"]')).toBeVisible({ timeout: 10_000 });
  });
});