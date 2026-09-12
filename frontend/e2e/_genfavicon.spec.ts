/**
 * 一次性工具：从 public/favicon.svg 重新生成 PNG 图标。
 *
 * 不参与正式回归（`_` 前缀已被 playwright.config.ts 的 testIgnore 排除）。
 * 需要重跑时把本文件临时改名为 favicon-gen.spec.ts，或去掉 config 里的 testIgnore，
 * 然后：npx playwright test _genfavicon.spec.ts --workers=1
 */
import { test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const PUBLIC = "E:/FN_Syn/Github/Moyu/frontend/public";

/** 用真实浏览器把 SVG 渲染成 PNG，供不支持 SVG favicon 的浏览器 / iOS 主屏图标使用。 */
test("generate favicon PNGs from the logo SVG", async ({ page }) => {
  test.setTimeout(60_000);

  const svg = readFileSync(join(PUBLIC, "favicon.svg"), "utf-8");
  // 生成时固定为品牌浅色版本（PNG 无法跟随主题）
  const lightSvg = svg.replace(/@media[\s\S]*?\}\s*\}/, "").replace(/#ececec/g, "#0d0d0d");

  for (const [size, name, bg] of [
    [32, "favicon-32x32.png", "transparent"],
    // iOS 会把主屏图标合成到不透明底上，透明背景会让深色描边看不见 → 用浅色磁贴
    [180, "apple-touch-icon.png", "#ffffff"],
  ] as const) {
    const html = `<!doctype html><html><head><style>
      html,body{margin:0;padding:0;background:${bg}}
      svg{display:block;width:${size}px;height:${size}px;box-sizing:border-box;padding:${Math.round(size * 0.16)}px}
    </style></head><body>${lightSvg}</body></html>`;
    const tmp = join(PUBLIC, `_tmp-${size}.html`);
    writeFileSync(tmp, html, "utf-8");
    await page.setViewportSize({ width: size, height: size });
    await page.goto(`file:///${tmp.replace(/\\/g, "/")}`);
    await page.screenshot({
      path: join(PUBLIC, name),
      omitBackground: bg === "transparent",
      clip: { x: 0, y: 0, width: size, height: size },
    });
  }
});