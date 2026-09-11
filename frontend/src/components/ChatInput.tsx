import { useState } from "react";

interface Props {
  streaming: boolean;
  onSend: (text: string) => void;
  onSkip: () => void;
}

export function ChatInput({ streaming, onSend, onSkip }: Props) {
  const [value, setValue] = useState("");

  const submit = () => {
    const text = value.trim();
    if (!text || streaming) return;
    onSend(text);
    setValue("");
  };

  return (
    <div className="chat-input">
      <input
        type="text"
        value={value}
        placeholder={streaming ? "AI 正在生成…" : "试试输入「下一章」"}
        disabled={streaming}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
      />
      {streaming ? (
        <button className="btn ghost" onClick={onSkip}>
          跳过
        </button>
      ) : (
        <button className="btn" onClick={submit}>
          发送
        </button>
      )}
    </div>
  );
}