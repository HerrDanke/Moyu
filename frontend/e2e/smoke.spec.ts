import { expect, test } from "@playwright/test";
import { importNovel, login, readingPercent, sendCommand } from "./helpers";

test("登录 → 导入小说 → 读下一章", async ({ page }) => {
  test.setTimeout(60_000);
  const chatStatuses: number[] = [];
  page.on("response", (resp) => {
    if (resp.url().includes("/api/chat")) chatStatuses.push(resp.status());
  });

  await login(page);
  await importNovel(page, "smoke");

  await sendCommand(page, "下一章");

  await expect(page.locator('[data-testid="message-user"]')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/青石阶/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('[data-testid="composer-input"]')).toBeEnabled({ timeout: 15_000 });

  expect(chatStatuses).toContain(200);
});

/**
 * 回归测试：自托管常用 http://<局域网IP> 访问，那是**非安全上下文**，
 * `crypto.randomUUID` 不存在。旧实现把它当作消息 ID 生成器直接调用，
 * 会在发送流程第一步抛 TypeError，导致请求完全发不出去。
 */
test("非安全上下文（明文 HTTP）下也能正常发送", async ({ page }) => {
  test.setTimeout(60_000);
  await page.addInitScript(() => {
    // @ts-expect-error 有意删除以复现明文 HTTP 环境
    delete (globalThis.crypto as Crypto).randomUUID;
  });

  const chatRequests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/chat")) chatRequests.push(r.url());
  });
  const pageErrors: string[] = [];
  page.on("pageerror", (e) => pageErrors.push(String(e)));

  await login(page);
  await importNovel(page, "nosecure");

  await sendCommand(page, "下一章");

  await expect(page.locator('[data-testid="message-user"]')).toBeVisible({ timeout: 10_000 });
  expect(chatRequests.length).toBeGreaterThan(0);
  expect(pageErrors.join("")).not.toContain("randomUUID");

  await expect(page.getByText(/章完/)).toBeVisible({ timeout: 30_000 });
});

/**
 * 回归测试：进度百分比必须**随阅读自行推进**，无需刷新页面。
 * 旧实现丢弃了 PATCH 的返回值，本地 progress state 从不更新。
 */
test("阅读时百分比自行推进（无需刷新页面）", async ({ page }) => {
  test.setTimeout(60_000);

  await login(page);
  await importNovel(page, "progress");

  await sendCommand(page, "下一章");

  await expect
    .poll(() => readingPercent(page), {
      timeout: 30_000,
      message: "百分比应随打字机进度自行上涨，而不是停在 0%",
    })
    .toBeGreaterThan(0);
});