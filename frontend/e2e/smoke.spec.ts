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