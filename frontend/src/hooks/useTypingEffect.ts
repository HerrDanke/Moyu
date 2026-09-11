import { useCallback, useEffect, useState } from "react";

export interface TypingState {
  displayed: string;
  isTyping: boolean;
  skip: () => void;
}

/**
 * 逐字显示 target 文本。target 增长（流式追加）时继续吐字；
 * 点击 skip 立即显示全部。
 */
export function useTypingEffect(
  target: string,
  charsPerTick = 2,
  tickMs = 16,
): TypingState {
  const [count, setCount] = useState(0);
  const [skipped, setSkipped] = useState(false);

  // target 变短（新消息）时重置
  useEffect(() => {
    if (count > target.length) setCount(target.length);
  }, [target, count]);

  useEffect(() => {
    if (skipped || count >= target.length) return;
    const id = window.setInterval(() => {
      setCount((c) => Math.min(c + charsPerTick, target.length));
    }, tickMs);
    return () => window.clearInterval(id);
  }, [count, target, skipped, charsPerTick, tickMs]);

  const skip = useCallback(() => setSkipped(true), []);

  const effective = skipped ? target.length : count;
  return {
    displayed: target.slice(0, effective),
    isTyping: effective < target.length,
    skip,
  };
}