import { expect, test, type Page } from "@playwright/test";
import { importGeneratedNovel, importNovel, login } from "./helpers";

async function sendVia(page: Page, testId: string) {
  await page.locator(`[data-testid="${testId}"]`).click();
}

test.describe("阅读快捷工具条与章节目录", () => {
  test("工具条只有翻页与目录，不含已移除的「跳转章节」", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "toolbar");

    const bar = page.locator('[data-testid="reading-toolbar"]');
    await expect(bar).toBeVisible();
    for (const id of ["toolbar-prev", "toolbar-next", "toolbar-toc"]) {
      await expect(page.locator(`[data-testid="${id}"]`)).toBeVisible();
    }
    // 回归护栏：「跳转章节」与「目录」功能重复，已被移除。若被重新加回，这里会失败。
    await expect(bar.locator("button")).toHaveCount(3);
    await expect(page.locator('[data-testid="toolbar-jump"]')).toHaveCount(0);
  });

  test("点「下一章」即可阅读（等价于手输指令）", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "toolnext");

    await sendVia(page, "toolbar-next");
    await expect(page.locator('[data-testid="message-user"]')).toContainText("下一章");
    await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 30_000 });
  });

  test("生成中禁用发送类按钮，但目录仍可用", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "tooldisabled");

    await sendVia(page, "toolbar-next");
    await expect(page.locator('[data-testid="toolbar-next"]')).toBeDisabled();
    await expect(page.locator('[data-testid="toolbar-prev"]')).toBeDisabled();
    await expect(page.locator('[data-testid="toolbar-toc"]')).toBeEnabled();

    await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('[data-testid="toolbar-next"]')).toBeEnabled();
  });

  test("手输「第 N 章」仍能跳章（去掉按钮后跳章能力不受影响）", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importNovel(page, "tooljump");

    const input = page.locator('[data-testid="composer-input"]');
    await input.fill("第 2 章");
    await input.press("Enter");
    await expect(page.locator('[data-testid="message-user"]')).toContainText("第 2 章");
    await expect(page.getByText(/第 2 章完/)).toBeVisible({ timeout: 30_000 });
  });

  /**
   * 回归：目录跳章必须走「当前」的 handleSend。
   *
   * 曾经这里用 `useCallback(..., [])` 包住 handlePickChapter，于是它永久闭包住首帧的
   * handleSend —— 那份里的 quickRead 恒为 false。症状是：用户打开「快速阅读」后从目录
   * 点章，服务端仍逐批慢推送，而前端打字机已被关掉，比点「下一章」还慢。
   *
   * 断言请求体而不是耗时：确定性、不受机器性能影响。
   */
  test("快速阅读在目录跳章这条路径上也生效", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await importGeneratedNovel(page, 6, "tocquick");

    const bodies: Array<Record<string, unknown>> = [];
    page.on("request", (r) => {
      if (!r.url().includes("/api/chat")) return;
      try {
        bodies.push(r.postDataJSON() as Record<string, unknown>);
      } catch {
        /* 非 JSON 请求体，忽略 */
      }
    });

    // 打开设置并启用「快速阅读」
    await page.locator('[data-testid="settings-button"]').click();
    const toggle = page.locator('[data-testid="quick-read-toggle"]');
    await expect(toggle).toHaveAttribute("aria-pressed", "false");
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "true");
    await page.locator('[data-testid="settings-close"]').click();

    // 从目录点第 3 章
    await sendVia(page, "toolbar-toc");
    const drawer = page.locator('[data-testid="toc-drawer"]');
    await expect(drawer).toBeVisible();
    await drawer.locator('[data-testid="toc-item-3"]').click();

    await expect.poll(() => bodies.length).toBeGreaterThan(0);
    expect(bodies[0].quick_read).toBe(true);
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

    await drawer.locator('[data-testid="toc-search"]').fill("标题18");
    await expect(drawer.locator('[data-testid="toc-item-18"]')).toBeVisible();
    await expect(drawer.locator('[data-testid="toc-item-8"]')).toHaveCount(0);

    // 关键：过滤后第 18 章是结果里的第 1 项。
    // 若实现误用「过滤结果的位次」而不是真实章号，这里就会跳到第 1 章。
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