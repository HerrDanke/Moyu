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

export async function login(page: Page) {
  await page.goto("/");
  const password = page.locator('[data-testid="login-password"]');
  if (await password.count()) {
    await password.fill(process.env.E2E_PASSWORD ?? "changeme");
    await page.locator('[data-testid="login-submit"]').click();
  }
}

export async function importNovel(page: Page, tag = "e2e") {
  const tmp = join(tmpdir(), `moyu-${tag}-${Date.now()}.txt`);
  writeFileSync(tmp, NOVEL, "utf-8");
  await page.locator('[data-testid="import-input"]').setInputFiles(tmp);
  await expect(page.getByText(/已导入/)).toBeVisible({ timeout: 15_000 });
}

/** 解析侧栏进度里的「本章 X%」；<1% 记作 0.5，便于断言“已经开始推进”。 */
export async function readingPercent(page: Page) {
  const text =
    (await page.locator('[data-testid="sidebar-progress"]').textContent()) ?? "";
  if (/本章\s*<1%/.test(text)) return 0.5;
  const m = text.match(/本章\s*(\d+)%/);
  return m ? Number(m[1]) : -1;
}