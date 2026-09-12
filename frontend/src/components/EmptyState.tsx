interface Props {
  bookTitle: string;
  chapterIndex: number;
  totalChapters: number;
  onCommand: (command: string) => void;
}

const EXAMPLES = ["下一章", "上一章", "跳到第 12 章", "书单"];

/**
 * 空状态：已选书但还没有任何消息。
 * 刻意不写「你好，我是你的阅读助手」这类无信息的问候，直接给可点的示例指令。
 */
export function EmptyState({
  bookTitle,
  chapterIndex,
  totalChapters,
  onCommand,
}: Props) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <h1 className="empty-title">继续读《{bookTitle}》</h1>
      <p className="empty-sub">
        上次读到第 {chapterIndex} / {totalChapters} 章
      </p>
      <div className="empty-chips">
        {EXAMPLES.map((cmd) => (
          <button
            key={cmd}
            type="button"
            className="chip"
            onClick={() => onCommand(cmd)}
          >
            {cmd}
          </button>
        ))}
      </div>
    </div>
  );
}