import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { useTypingEffect } from "../hooks/useTypingEffect";

interface BubbleProps {
  message: ChatMessage;
  animate: boolean;
  onProgress?: (revealedLength: number) => void;
}

function AssistantBubble({ message, animate, onProgress }: BubbleProps) {
  const { displayed, isTyping, skip } = useTypingEffect(message.text);
  const shown = animate ? displayed : message.text;
  const typing = animate && isTyping;
  const showThinking = message.streaming && !shown && !!message.thinking;

  useEffect(() => {
    if (typing && onProgress) onProgress(shown.length);
  }, [shown.length, typing, onProgress]);

  return (
    <div className="msg assistant">
      <div className="bubble">
        {showThinking ? (
          <span className="thinking">
            {message.thinking}
            <span className="caret" />
          </span>
        ) : (
          <>
            <span className="assistant-text">{shown}</span>
            {typing && <span className="caret" />}
          </>
        )}
      </div>
      {typing && (
        <button className="link-btn" onClick={skip}>
          跳过输入
        </button>
      )}
    </div>
  );
}

function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="msg user">
      <div className="bubble">{message.text}</div>
    </div>
  );
}

interface Props {
  messages: ChatMessage[];
  animate?: boolean;
  onProgress?: (revealedLength: number) => void;
}

export function MessageList({ messages, animate = true, onProgress }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.length === 0 && (
        <div className="empty-hint">
          <h2>你好，我是你的阅读助手</h2>
          <p>导入一本书，然后对我说「下一章」开始阅读。</p>
        </div>
      )}
      {messages.map((m) =>
        m.role === "user" ? (
          <UserBubble key={m.id} message={m} />
        ) : (
          <AssistantBubble
            key={m.id}
            message={m}
            animate={animate}
            onProgress={onProgress}
          />
        ),
      )}
      <div ref={endRef} />
    </div>
  );
}