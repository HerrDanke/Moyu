/**
 * 生成消息 ID。
 *
 * 重要：`crypto.randomUUID()` 只在**安全上下文**（HTTPS 或 localhost）存在。
 * 自托管场景常用 `http://<局域网IP>:端口` 访问，此时它是 undefined，
 * 直接调用会抛 `TypeError: crypto.randomUUID is not a function`，
 * 并且因为它是发送流程的第一步，会导致**请求完全发不出去**。
 *
 * 因此这里做能力检测 + 回退，保证明文 HTTP 部署也能正常工作。
 */
export function newId(): string {
  const cryptoObj: Crypto | undefined = globalThis.crypto;
  if (cryptoObj && typeof cryptoObj.randomUUID === "function") {
    return cryptoObj.randomUUID();
  }
  const a = Math.random().toString(36).slice(2, 10);
  const b = Math.random().toString(36).slice(2, 10);
  return `id-${Date.now().toString(36)}-${a}${b}`;
}