interface Props {
  bookTitle: string;
  chapterIndex: number;
  totalChapters: number;
  offset: number;
  chapterChars: number;
}

export function ChapterProgress({
  bookTitle,
  chapterIndex,
  totalChapters,
  offset,
  chapterChars,
}: Props) {
  const percent =
    chapterChars > 0 ? Math.min(100, Math.round((offset / chapterChars) * 100)) : 0;
  return (
    <div className="chapter-progress">
      《{bookTitle}》第 {chapterIndex} / {totalChapters} 章
      {chapterChars > 0 && ` · 已完成 ${percent}%`}
    </div>
  );
}