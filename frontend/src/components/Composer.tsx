import { useEffect, type RefObject } from "react";

interface Props {
  streaming: boolean;
  /** 输入框草稿（由 App 受控持有） */
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: (text: string) => void;
  onStop: () => void;
  inputRef?: RefObject<HTMLTextAreaElement>;
}

export function Composer({
  streaming,
  draft,
  onDraftChange,
  onSend,
  onStop,
  inputRef,
}: Props) {
  // auto-grow（上限 200px）
  useEffect(() => {
    const el = inputRef?.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [draft, inputRef]);

  const submit = () => {
    const text = draft.trim();
    if (!text || streaming) return;
    onSend(text);
    onDraftChange("");
  };

  return (
    <div className="composer">
      <textarea
        ref={inputRef}
        data-testid="composer-input"
        className="composer-input"
        rows={1}
        value={draft}
        placeholder={streaming ? "正在生成…" : "说「下一章」继续阅读…"}
        disabled={streaming}
        onChange={(e) => onDraftChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      {streaming ? (
        <button
          type="button"
          className="composer-btn is-stop"
          data-testid="stop-button"
          title="停止生成"
          aria-label="停止生成"
          onClick={onStop}
        >
          <span className="stop-square" aria-hidden="true" />
        </button>
      ) : (
        <button
          type="button"
          className="composer-btn"
          data-testid="send-button"
          title="发送"
          aria-label="发送"
          disabled={!draft.trim()}
          onClick={submit}
        >
          <span aria-hidden="true">↑</span>
        </button>
      )}
    </div>
  );
}