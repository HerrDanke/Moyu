import type {
  Book,
  ChapterMeta,
  ImportResult,
  Progress,
  StreamEvent,
} from "../types";

const BASE: string = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export async function getAuthStatus(): Promise<{
  password_required: boolean;
  authenticated: boolean;
}> {
  return handle(await fetch(`${BASE}/api/auth/status`));
}

export async function login(password: string): Promise<void> {
  await handle(
    await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    }),
  );
}

export async function logout(): Promise<void> {
  await handle(await fetch(`${BASE}/api/auth/logout`, { method: "POST" }));
}

export async function listBooks(): Promise<Book[]> {
  return handle(await fetch(`${BASE}/api/books`));
}

export async function importBook(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  return handle(await fetch(`${BASE}/api/books/import`, { method: "POST", body: form }));
}

export async function deleteBook(id: number): Promise<void> {
  await handle(await fetch(`${BASE}/api/books/${id}`, { method: "DELETE" }));
}

export async function getChapters(bookId: number): Promise<ChapterMeta[]> {
  return handle(await fetch(`${BASE}/api/books/${bookId}/chapters`));
}

export async function getProgress(bookId: number): Promise<Progress> {
  return handle(await fetch(`${BASE}/api/progress/${bookId}`));
}

export async function patchProgress(
  bookId: number,
  payload: { chapter_index?: number; chapter_offset?: number },
): Promise<Progress> {
  return handle(
    await fetch(`${BASE}/api/progress/${bookId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

/**
 * POST /api/chat 并以 SSE 读取流式响应。
 * 返回一个 abort 函数用于「跳过生成」。
 */
export function streamChat(
  message: string,
  onEvent: (event: StreamEvent) => void,
  opts: { quickRead?: boolean } = {},
): { abort: () => void; done: Promise<void> } {
  const controller = new AbortController();

  const done = (async () => {
    const resp = await fetch(`${BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, quick_read: !!opts.quickRead }),
      signal: controller.signal,
    });
    if (!resp.ok || !resp.body) {
      throw new ApiError(resp.status, "对话请求失败");
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done: finished } = await reader.read();
      if (finished) break;
      buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        for (const line of raw.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") return;
          try {
            onEvent(JSON.parse(data) as StreamEvent);
          } catch {
            /* 忽略非 JSON 行 */
          }
        }
      }
    }
  })();

  return { abort: () => controller.abort(), done };
}