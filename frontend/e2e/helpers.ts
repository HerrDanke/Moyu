import { expect, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const NOVEL = `第一章 初入江湖

夜色如墨，韩立站在青石阶前，望着那巍峨的山门。
灵光流转，一道玉符悬于半空。

第二章 灵光乍现

晨光微露，他睁开眼，发现体内多了一缕灵气。
`;

export const ADMIN_USERNAME = process.env.E2E_USERNAME ?? "admin";
export const ADMIN_PASSWORD = process.env.E2E_PASSWORD ?? "admin-pass-1234";

/**
 * 登录。若服务尚未初始化（首次引导页），需要 E2E_SETUP_CODE
 * （该口令只在服务端启动日志里）。
 */
export async function login(page: Page, username = ADMIN_USERNAME, password = ADMIN_PASSWORD) {
  await page.goto("/");

  const setupCode = page.locator('[data-testid="setup-code"]');
  if (await setupCode.count()) {
    const code = process.env.E2E_SETUP_CODE;
    if (!code) {
      throw new Error(
        "服务尚未初始化：请先在服务器上完成首次引导，或提供 E2E_SETUP_CODE 环境变量",
      );
    }
    await page.locator('[data-testid="setup-username"]').fill(username);
    await page.locator('[data-testid="setup-password"]').fill(password);
    await setupCode.fill(code);
    await page.locator('[data-testid="setup-submit"]').click();
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible({ timeout: 15_000 });
    return;
  }

  const userInput = page.locator('[data-testid="login-username"]');
  if (await userInput.count()) {
    await userInput.fill(username);
    await page.locator('[data-testid="login-password"]').fill(password);
    await page.locator('[data-testid="login-submit"]').click();
  }
  await expect(page.locator('[data-testid="sidebar"]')).toBeVisible({ timeout: 15_000 });
}

/** 管理员创建一个新用户，返回其用户名/密码，供隔离类用例使用。 */
export async function createUserViaUi(
  page: Page,
  username: string,
  password: string,
): Promise<void> {
  await page.locator('[data-testid="user-admin-entry"]').click();
  await expect(page.locator('[data-testid="user-admin-dialog"]')).toBeVisible();
  await page.locator('[data-testid="new-user-name"]').fill(username);
  await page.locator('[data-testid="new-user-password"]').fill(password);
  await page.locator('[data-testid="create-user-submit"]').click();
  await expect(page.getByText(username, { exact: false })).toBeVisible({ timeout: 10_000 });
  await page.locator('[data-testid="user-admin-close"]').click();
  await expect(page.locator('[data-testid="user-admin-dialog"]')).toBeHidden();
}

/** 打开设置面板（主题/阅读宽度/快速阅读/退出登录 现在都在里面）。 */
export async function openSettings(page: Page) {
  await page.locator('[data-testid="settings-button"]').click();
  await expect(page.locator('[data-testid="settings-dialog"]')).toBeVisible();
}

/** 设置「思考强度」档位（1 迅捷 / 2 标准 / 3 深入 / 4 沉思），并等保存完成。 */
export async function setThinkingLevel(page: Page, level: number) {
  await openSettings(page);
  const slider = page.locator('[data-testid="thinking-slider"]');
  await slider.fill(String(level));
  await expect(page.locator('[data-testid="thinking-label"]')).not.toHaveText("—");
  await page.locator('[data-testid="settings-close"]').click();
  await expect(page.locator('[data-testid="settings-dialog"]')).toBeHidden();
}

/**
 * 导入一本「节奏可测」的书：每章 8 句，便于用「收尾出现耗时」观测生成速度。
 */
export async function importPacedNovel(page: Page, tag = "paced") {
  const sentences = (n: number) =>
    Array.from({ length: n }, (_, i) => `这是第 ${i + 1} 句正文，用来观测出字节奏。`).join("\n");
  const text = [
    `第1章 节奏一\n${sentences(8)}`,
    `第2章 节奏二\n${sentences(8)}`,
    `第3章 节奏三\n${sentences(8)}`,
  ].join("\n\n");
  const tmp = join(tmpdir(), `moyu-${tag}-${Date.now()}.txt`);
  writeFileSync(tmp, text, "utf-8");
  await page.locator('[data-testid="import-input"]').setInputFiles(tmp);
  await expect(page.getByText(/共 3 章/)).toBeVisible({ timeout: 15_000 });
}

/** 发一条指令并返回「从发送到收尾文案出现」的毫秒数。 */
export async function measureStreamMs(page: Page, command: string) {
  const t0 = Date.now();
  const input = page.locator('[data-testid="composer-input"]');
  await input.fill(command);
  await input.press("Enter");
  await expect(page.locator('[data-testid="stop-button"]')).toBeHidden({ timeout: 120_000 });
  return Date.now() - t0;
}

export async function importNovel(page: Page, tag = "e2e") {
  const tmp = join(tmpdir(), `moyu-${tag}-${Date.now()}.txt`);
  writeFileSync(tmp, NOVEL, "utf-8");
  await page.locator('[data-testid="import-input"]').setInputFiles(tmp);
  await expect(page.getByText(/已导入/)).toBeVisible({ timeout: 15_000 });
}

/** 生成一本多章的书，用于验证目录的窗口化（只渲染可视区域）。 */
export async function importGeneratedNovel(
  page: Page,
  chapterCount: number,
  tag = "big",
) {
  const parts: string[] = [];
  for (let i = 1; i <= chapterCount; i += 1) {
    parts.push(`第${i}章 标题${i}\n这是第 ${i} 章的正文内容。\n`);
  }
  const tmp = join(tmpdir(), `moyu-${tag}-${Date.now()}.txt`);
  writeFileSync(tmp, parts.join("\n"), "utf-8");
  await page.locator('[data-testid="import-input"]').setInputFiles(tmp);
  await expect(page.getByText(new RegExp(`共 ${chapterCount} 章`))).toBeVisible({
    timeout: 30_000,
  });
}

/** 解析侧栏进度里的「本章 X%」；<1% 记作 0.5，便于断言“已经开始推进”。 */
export async function readingPercent(page: Page) {
  const text = (await page.locator('[data-testid="sidebar-progress"]').textContent()) ?? "";
  if (/本章\s*<1%/.test(text)) return 0.5;
  const m = text.match(/本章\s*(\d+)%/);
  return m ? Number(m[1]) : -1;
}