interface Props {
  bookTitle: string;
  chapterIndex: number;
  totalChapters: number;
}

/**
 * 空状态：已选书但还没有任何消息。
 *
 * 这里刻意**不再放**「下一章 / 上一章」这类按钮 —— 它们已经在输入框上方的
 * 阅读工具条里常驻了，重复只会显得啰嗦。这里只交代「你在哪」与「怎么开始」。
 */
export function EmptyState({ bookTitle, chapterIndex, totalChapters }: Props) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <h1 className="empty-title">继续读《{bookTitle}》</h1>
      <p className="empty-sub">
        上次读到第 {chapterIndex} / {totalChapters} 章
      </p>
      <p className="empty-hint">
        用下面的按钮翻页或打开目录，也可以直接打字告诉我，比如「跳到第 12 章」。
      </p>
    </div>
  );
}