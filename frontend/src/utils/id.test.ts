import { afterEach, describe, expect, test, vi } from "vitest";
import { newId } from "./id";

describe("newId", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("安全上下文下优先使用 crypto.randomUUID", () => {
    const spy = vi.fn(() => "11111111-2222-4333-8444-555555555555");
    vi.stubGlobal("crypto", { randomUUID: spy });
    expect(newId()).toBe("11111111-2222-4333-8444-555555555555");
    expect(spy).toHaveBeenCalledTimes(1);
  });

  // 回归测试：http://<局域网IP> 属非安全上下文，crypto.randomUUID 不存在。
  // 旧实现直接调用会抛 TypeError 并中断整个发送流程（请求发不出去）。
  test("非安全上下文（无 randomUUID）下不抛异常", () => {
    vi.stubGlobal("crypto", {});
    expect(() => newId()).not.toThrow();
    expect(typeof newId()).toBe("string");
  });

  test("回退实现仍能保证唯一性", () => {
    vi.stubGlobal("crypto", {});
    const ids = new Set(Array.from({ length: 500 }, () => newId()));
    expect(ids.size).toBe(500);
  });

  test("crypto 整体缺失时也能工作", () => {
    vi.stubGlobal("crypto", undefined);
    expect(typeof newId()).toBe("string");
    expect(newId().length).toBeGreaterThan(0);
  });
});