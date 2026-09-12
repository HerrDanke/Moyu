import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { useTypingEffect } from "../hooks/useTypingEffect";

interface BubbleProps {
  message: ChatMessage;
  animate: boolean;
  charsPerTick: number;
  onProgress?: (messageId: string, revealedLength: number) => void;
}

/** 把助手文本切成「章节标题 / 正文 / 收尾」三段，标题单独成块才有层次。 */
export function splitAssistantText(text: string, bodyStart?: number) {
  let rest = text;
  let title = "";
  if (bodyStart && bodyStart > 0 && text.length >= bodyStart) {
    title = text.slice(0, bodyStart).trim();
    rest = text.slice(bodyStart);
  }
  let footer = "";
  const idx = rest.lastIndexOf("\n\n");
  if (idx >= 0) {
    const tail = rest.slice(idx + 2).trim();
    if (/^第\s*\d+\s*章完/.test(tail)) {
      footer = tail;
      rest = rest.slice(0, idx);
    }
  }
  return { title, body: rest, footer };
}

function AssistantMessage({ message, animate, charsPerTick, onProgress }: BubbleProps) {
  const { displayed, isTyping, skip } = useTypingEffect(message.text, charsPerTick);
  const shown = animate ? displayed : message.text;
  const typing = animate && isTyping;
  const generating = !!message.streaming && !shown.trim();
  const { title, body, footer } = splitAssistantText(shown, message.bodyStart);
  // 中文 TXT 小说通常「一行 = 一段」，按换行切段才能在行距之外留出段间距
  const paragraphs = body
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);

  useEffect(() => {
    if (!onProgress) return;
    if (animate) {
      if (typing) onProgress(message.id, shown.length);
    } else if (!message.streaming && message.text) {
      // 快速阅读：无打字机动画，流式结束即视为本章已读完
      onProgress(message.id, message.text.length);
    }
  }, [
    shown.length,
    typing,
    animate,
    message.id,
    message.streaming,
    message.text,
    onProgress,
  ]);

  return (
    <div className="msg assistant" data-testid="message-assistant">
      {generating ? (
        <div className="generating">
          <span className="dots" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          {message.thinking && <span className="generating-text">{message.thinking}</span>}
        </div>
      ) : (
        <div className="assistant-body">
          {title && <h2 className="chapter-title">{title}</h2>}
          <div className="chapter-text">
            {paragraphs.map((p, i) => (
              <p key={i} className="para">
                {p}
                {typing && i === paragraphs.length - 1 && <span className="caret" />}
              </p>
            ))}
            {typing && paragraphs.length === 0 && (
              <p className="para">
                <span className="caret" />
              </p>
            )}
          </div>
          {footer && <p className="chapter-footer">{footer}</p>}
        </div>
      )}
      {typing && (
        <button type="button" className="link-btn" onClick={skip}>
          跳过输入
        </button>
      )}
    </div>
  );
}

function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="msg user" data-testid="message-user">
      <div className="bubble">{message.text}</div>
    </div>
  );
}

interface Props {
  messages: ChatMessage[];
  animate?: boolean;
  /** 当前「思考强度」对应的速度倍率：用来缩放打字机速率 */
  typingSpeed?: number;
  onProgress?: (messageId: string, revealedLength: number) => void;
}

export function MessageList({
  messages,
  animate = true,
  typingSpeed = 1,
  onProgress,
}: Props) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  // 打字机速率随「思考强度」缩放：倍率 1.0 → 2 字/16ms（原行为），4.0 → 8 字/16ms。
  // 不缩放的话，无论服务端多快，长章节都会被 125 字/秒的动画拖住。
  const charsPerTick = useMemo(
    () => Math.min(24, Math.max(1, Math.round(2 * typingSpeed))),
    [typingSpeed],
  );

  const lastStreaming = [...messages].reverse().find((m) => m.role === "assistant" && m.streaming);

  // 自动跟随：非平滑滚动，且仅在用户已位于底部时生效
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || !atBottom) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, atBottom]);

  const handleScroll = () => {
    const el = scrollerRef.current;
    if (!el) return;
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80);
  };

  return (
    <div className="thread-wrap">
      <div className="thread" ref={scrollerRef} onScroll={handleScroll}>
        {messages.map((m) =>
          m.role === "user" ? (
            <UserMessage key={m.id} message={m} />
          ) : (
            <AssistantMessage
              key={m.id}
              message={m}
              animate={animate}
              charsPerTick={charsPerTick}
              onProgress={onProgress}
            />
          ),
        )}
      </div>
      <span className="sr-only" aria-live="polite">
        {lastStreaming?.chapterIndex
          ? `正在生成第 ${lastStreaming.chapterIndex} 章`
          : lastStreaming
            ? "正在生成"
            : ""}
      </span>
      {!atBottom && (
        <button
          type="button"
          className="jump-bottom"
          onClick={() => {
            const el = scrollerRef.current;
            if (el) el.scrollTop = el.scrollHeight;
            setAtBottom(true);
          }}
        >
          回到底部
        </button>
      )}
    </div>
  );
}