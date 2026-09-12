interface Props {
  /** 流式生成中：发送类按钮禁用（与输入框一致） */
  sendingDisabled: boolean;
  onSend: (command: string) => void;
  onOpenToc: () => void;
}

/**
 * 输入框上方的常驻快捷操作。发送类按钮复用既有指令，不新增后端能力。
 *
 * 注意：这里刻意只保留「翻页」与「目录」。
 * 「跳转章节」（预填 `第 ` 让用户补数字）曾存在，但与「目录」的搜索+点选完全重叠，
 * 徒增一个入口，故移除。需要跳章时走目录，或直接手输「第 N 章」。
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
        data-testid="toolbar-toc"
        onClick={onOpenToc}
      >
        目录
      </button>
    </div>
  );
}
