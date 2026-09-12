/** 本章进度文案：避免与「整本书进度」混淆，且极小进度不显示为 0%。 */
export function formatProgressLabel(
  chapterIndex: number,
  totalChapters: number,
  offset: number,
  chapterChars: number,
): string {
  const base = `第 ${chapterIndex} / ${totalChapters} 章`;
  if (chapterChars <= 0) return base;
  const ratio = Math.min(1, Math.max(0, offset / chapterChars));
  if (ratio <= 0) return `${base} · 本章 0%`;
  const percent = Math.round(ratio * 100);
  if (percent < 1) return `${base} · 本章 <1%`;
  return `${base} · 本章 ${percent}%`;
}