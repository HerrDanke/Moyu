interface Props {
  /** 流式生成中：发送类按钮禁用（与输入框一致） */
  sendingDisabled: boolean;
  onSend: (command: string) => void;
  onOpenToc: () => void;
  onJump: () => void;
}

/** 输入框上方的常驻快捷操作。发送类按钮复用既有指令，不新增后端能力。 */
export function ReadingToolbar({
  sendingDisabled,
  onSend,
  onOpenToc,
  onJump,
}: Props) {
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
      <button
        type="button"
        className="tool-btn"
        data-testid="toolbar-jump"
        onClick={onJump}
      >
        跳转章节
      </button>
    </div>
  );
}