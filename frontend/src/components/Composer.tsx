import { useEffect, useRef, useState } from "react";

interface Props {
  streaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

export function Composer({ streaming, onSend, onStop }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  // auto-grow（上限 200px）
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || streaming) return;
    onSend(text);
    setValue("");
  };

  return (
    <div className="composer">
      <textarea
        ref={ref}
        data-testid="composer-input"
        className="composer-input"
        rows={1}
        value={value}
        placeholder={streaming ? "正在生成…" : "说「下一章」继续阅读…"}
        disabled={streaming}
        onChange={(e) => setValue(e.target.value)}
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
          disabled={!value.trim()}
          onClick={submit}
        >
          <span aria-hidden="true">↑</span>
        </button>
      )}
    </div>
  );
}