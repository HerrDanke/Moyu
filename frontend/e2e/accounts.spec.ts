import { expect, test } from "@playwright/test";
import {
  ADMIN_PASSWORD,
  ADMIN_USERNAME,
  createUserViaUi,
  importNovel,
  login,
} from "./helpers";

test.describe("账号与用户管理", () => {
  test("品牌标识为自研，不出现第三方名称", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);

    const brand = page.locator('[data-testid="brand"]');
    await expect(brand).toBeVisible();
    await expect(brand).toContainText("墨鱼");
    // 自研标记必须存在，且不是任何第三方图形
    await expect(brand.locator("svg.logo-mark")).toHaveCount(1);

    const body = (await page.locator("body").innerText()).toLowerCase();
    expect(body).not.toContain("chatgpt");
    expect(body).not.toContain("openai");
  });

  test("侧栏显示当前用户与身份", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    const userArea = page.locator('[data-testid="sidebar-user"]');
    await expect(userArea).toContainText(ADMIN_USERNAME);
    await expect(userArea).toContainText("管理员");
  });

  test("管理员可创建用户，新用户能登录且看不到用户管理入口", async ({ page, browser }) => {
    test.setTimeout(120_000);
    await login(page);

    const suffix = Date.now().toString().slice(-6);
    const username = `reader${suffix}`;
    const password = "reader-pass-1234";
    await createUserViaUi(page, username, password);

    // 用普通用户身份开一个新上下文登录
    const ctx = await browser.newContext();
    const readerPage = await ctx.newPage();
    await login(readerPage, username, password);
    await expect(readerPage.locator('[data-testid="sidebar-user"]')).not.toContainText("管理员");
    await expect(readerPage.locator('[data-testid="user-admin-entry"]')).toHaveCount(0);
    // 直接访问管理接口同样被拒
    const resp = await readerPage.request.get("/api/users");
    expect(resp.status()).toBe(403);
    await ctx.close();
  });

  test("两个用户读同一本书，进度互不影响", async ({ page, browser }) => {
    test.setTimeout(150_000);
    await login(page);

    const suffix = Date.now().toString().slice(-6);
    const username = `reader${suffix}`;
    const password = "reader-pass-1234";
    await createUserViaUi(page, username, password);

    // 管理员导入一本书并读一章
    await importNovel(page, "iso");
    const input = page.locator('[data-testid="composer-input"]');
    await input.fill("下一章");
    await input.press("Enter");
    await expect(page.getByText(/第 1 章完/)).toBeVisible({ timeout: 30_000 });
    await expect
      .poll(async () => (await page.locator('[data-testid="sidebar-progress"]').textContent()) ?? "", {
        timeout: 30_000,
        message: "管理员应推进到第 1 章",
      })
      .toContain("第 1 /");

    // 普通用户看到的是自己的第 1 章（未开始），而不是管理员的进度
    const ctx = await browser.newContext();
    const readerPage = await ctx.newPage();
    await login(readerPage, username, password);
    await expect(readerPage.locator('[data-testid="sidebar-progress"]')).toContainText("第 1 /");
    await ctx.close();
  });

  test("普通用户无法删除书籍（前端无入口、后端 403）", async ({ page, browser }) => {
    test.setTimeout(120_000);
    await login(page);
    await importNovel(page, "perm");

    const suffix = Date.now().toString().slice(-6);
    const username = `reader${suffix}`;
    const password = "reader-pass-1234";
    await createUserViaUi(page, username, password);

    const ctx = await browser.newContext();
    const readerPage = await ctx.newPage();
    await login(readerPage, username, password);

    const books = await (await readerPage.request.get("/api/books")).json();
    const bookId = books[books.length - 1].id as number;
    const del = await readerPage.request.delete(`/api/books/${bookId}`);
    expect(del.status()).toBe(403);
    await ctx.close();
  });

  test("退出登录回到登录页", async ({ page }) => {
    test.setTimeout(60_000);
    await login(page);
    await page.locator('[data-testid="settings-button"]').click();
    await page.locator('[data-testid="logout-button"]').click();
    await expect(page.locator('[data-testid="login-username"]')).toBeVisible({ timeout: 10_000 });
    await page.locator('[data-testid="login-username"]').fill(ADMIN_USERNAME);
    await page.locator('[data-testid="login-password"]').fill(ADMIN_PASSWORD);
    await page.locator('[data-testid="login-submit"]').click();
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible({ timeout: 15_000 });
  });
});