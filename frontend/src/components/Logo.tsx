/**
 * 项目自有的极简标识（原创几何造型：墨滴 + 内凹弧线）。
 *
 * 刻意不使用 OpenAI / ChatGPT 的名称或图形——那属于对方商标，
 * 且会让使用者误以为本应用与 OpenAI 有关联。视觉语言（单色、克制的线条）
 * 可以与同类产品对齐，但标识本身必须是原创的。
 */
export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className="logo-mark"
    >
      <path
        d="M12 3c4 3.9 6.4 7 6.4 9.9a6.4 6.4 0 0 1-12.8 0C5.6 10 8 6.9 12 3Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M9.3 13.5c1.2 1.5 4.2 1.5 5.4 0"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}