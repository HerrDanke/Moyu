interface Props {
  /** 流式生成中：发送类按钮禁用（与输入框一致） */
  sendingDisabled: boolean;
  onSend: (command: string) => void;
  onOpenToc: () => void;
}

/**
 * 输入框上方的常驻快捷操作。每个按钮只发出一条指令并走同一套 `/api/chat` 流式管道，
 * 前端不新增任何阅读逻辑（因此不会出现「按钮路径」与「手输路径」行为不一致的问题）。
 *
 * 为什么不设「跳转章节」按钮：「目录」（搜索 + 点选）与手输「第 N 章」已经完全覆盖跳章，
 * 再放一个预填输入的按钮只是徒增入口。
 *
 * 为什么需要「继续本章」：中途停下后，「下一章」会跳到下一章、「第 N 章」会从头重放，
 * 会话内没有任何入口能接着读本章剩下的部分——只有刷新页面或切走再切回才会用断点续读。
 * 这个按钮补的正是这个空白（语义是"续读"而非"重放"）。
 */
export function ReadingToolbar({ sendingDisabled, onSend, onOpenToc }: Props) {
  return (
    <div className="reading-toolbar" data-testid="reading-toolbar">
      <button
        type="button"
        className="tool-btn"
        data-testid="toolbar-prev"
        disabled={sendingDisabled}
        onClick={() => onSend("上一章")}
      >
        上一章
      </button>
      <button
        type="button"
        className="tool-btn"
        data-testid="toolbar-next"
        disabled={sendingDisabled}
        onClick={() => onSend("下一章")}
      >
        下一章
      </button>
      <button
        type="button"
        className="tool-btn"
        data-testid="toolbar-resume"
        disabled={sendingDisabled}
        onClick={() => onSend("继续本章")}
      >
        继续本章
      </button>
      <button
        type="button"
        className="tool-btn"
        data-testid="toolbar-toc"
        onClick={onOpenToc}
      >
        目录
      </button>
    </div>
  );
}
