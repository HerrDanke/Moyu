import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { useTypingEffect } from "./useTypingEffect";

describe("useTypingEffect", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  test("逐字显示并在到达末尾后停止", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useTypingEffect("abcdef", 2, 16));
    expect(result.current.displayed).toBe("");
    expect(result.current.isTyping).toBe(true);

    act(() => {
      vi.advanceTimersByTime(16);
    });
    expect(result.current.displayed).toBe("ab");

    act(() => {
      vi.advanceTimersByTime(16);
    });
    expect(result.current.displayed).toBe("abcd");

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayed).toBe("abcdef");
    expect(result.current.isTyping).toBe(false);
  });

  test("skip 立即显示全部", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useTypingEffect("hello world", 1, 16));
    act(() => {
      result.current.skip();
    });
    expect(result.current.displayed).toBe("hello world");
    expect(result.current.isTyping).toBe(false);
  });

  test("target 增长时继续吐字（模拟流式追加）", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ t }) => useTypingEffect(t, 10, 16), {
      initialProps: { t: "abc" },
    });
    act(() => {
      vi.advanceTimersByTime(16);
    });
    expect(result.current.displayed).toBe("abc");
    rerender({ t: "abcdef" });
    act(() => {
      vi.advanceTimersByTime(16);
    });
    expect(result.current.displayed).toBe("abcdef");
  });
});