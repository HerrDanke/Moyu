import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const NOVEL = `第一章 初入江湖

夜色如墨，韩立站在青石阶前，望着那巍峨的山门。
灵光流转，一道玉符悬于半空。

第二章 灵光乍现

晨光微露，他睁开眼，发现体内多了一缕灵气。
`;

test("登录 → 导入小说 → 读下一章", async ({ page }) => {
  // 记录对话请求是否成功发起（流式响应体由断言页面内容来验证）
  const chatStatuses: number[] = [];
  page.on("response", (resp) => {
    if (resp.url().includes("/api/chat")) chatStatuses.push(resp.status());
  });

  await page.goto("/");

  // 若配置了访问密码，先登录
  const password = page.locator('input[type="password"]');
  if (await password.count()) {
    await password.fill(process.env.E2E_PASSWORD ?? "changeme");
    await page.getByRole("button", { name: "进入" }).click();
  }

  // 导入 TXT
  const tmp = join(tmpdir(), `moyu-e2e-${Date.now()}.txt`);
  writeFileSync(tmp, NOVEL, "utf-8");
  await page.locator('input[type="file"]').setInputFiles(tmp);

  await expect(page.getByText(/已导入/)).toBeVisible({ timeout: 10_000 });

  // 发「下一章」
  const input = page.getByPlaceholder(/下一章/);
  await input.fill("下一章");
  await input.press("Enter");

  // 正文出现
  await expect(page.getByText(/青石阶/)).toBeVisible({ timeout: 15_000 });
  // 收尾文案出现 = 整段流式已完成
  await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 15_000 });
  // 输入框恢复可用
  await expect(input).toBeEnabled({ timeout: 15_000 });

  expect(chatStatuses).toContain(200);
});

/**
 * 回归测试：自托管常用 http://<局域网IP> 访问，那是**非安全上下文**，
 * `crypto.randomUUID` 不存在。旧实现把它当作消息 ID 生成器直接调用，
 * 会在发送流程第一步抛 TypeError，导致请求完全发不出去（界面看似卡住、进度永远 0%）。
 */
test("非安全上下文（明文 HTTP）下也能正常发送", async ({ page }) => {
  // 模拟 non-secure context：删除仅在安全上下文可用的 API
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

  await page.goto("/");
  const password = page.locator('input[type="password"]');
  if (await password.count()) {
    await password.fill(process.env.E2E_PASSWORD ?? "changeme");
    await page.getByRole("button", { name: "进入" }).click();
  }

  // 保证有书可选
  const options = await page.locator(".book-selector select option").count();
  if (options <= 1) {
    const tmp = join(tmpdir(), `moyu-e2e-nosecure-${Date.now()}.txt`);
    writeFileSync(tmp, NOVEL, "utf-8");
    await page.locator('input[type="file"]').setInputFiles(tmp);
    await expect(page.getByText(/已导入/)).toBeVisible({ timeout: 15_000 });
  }

  const input = page.getByPlaceholder(/下一章/);
  await input.fill("下一章");
  await input.press("Enter");

  // 用户气泡必须出现，且真的发出了 /api/chat
  await expect(page.locator(".msg.user")).toBeVisible({ timeout: 10_000 });
  expect(chatRequests.length).toBeGreaterThan(0);
  expect(pageErrors.join("")).not.toContain("randomUUID");
});