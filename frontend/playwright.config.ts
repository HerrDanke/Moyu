import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  // 目标环境是单核自托管机器：并行 worker 会把后端压到超时，
  // 产生与本仓库代码无关的偶发失败。串行换取确定性。
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000",
    headless: true,
  },
});