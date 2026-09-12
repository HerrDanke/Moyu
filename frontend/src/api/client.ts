import type {
  AuthStatus,
  Book,
  ChapterMeta,
  ImportResult,
  Progress,
  StreamEvent,
  User,
} from "../types";

const BASE: string = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let unauthorizedHandler: (() => void) | null = null;

/** 注册全局 401 处理（会话过期时回到登录页）。 */
export function onUnauthorized(fn: () => void): void {
  unauthorizedHandler = fn;
}

async function handle<T>(resp: Response, opts: { auth?: boolean } = {}): Promise<T> {
  if (!resp.ok) {
    if (resp.status === 401 && !opts.auth) unauthorizedHandler?.();
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

export async function getAuthStatus(): Promise<AuthStatus> {
  return handle(await fetch(`${BASE}/api/auth/status`));
}

export async function login(username: string, password: string): Promise<User> {
  return handle(
    await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
    { auth: true },
  );
}

export async function setup(
  username: string,
  password: string,
  setupCode: string,
): Promise<User> {
  return handle(
    await fetch(`${BASE}/api/auth/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, setup_code: setupCode }),
    }),
    { auth: true },
  );
}

export async function getMe(): Promise<User> {
  return handle(await fetch(`${BASE}/api/auth/me`));
}

// --------------------------------------------------------------------------
// 用户管理（管理员）
// --------------------------------------------------------------------------
export async function listUsers(): Promise<User[]> {
  return handle(await fetch(`${BASE}/api/users`));
}

export async function createUser(
  username: string,
  password: string,
  isAdmin: boolean,
): Promise<User> {
  return handle(
    await fetch(`${BASE}/api/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, is_admin: isAdmin }),
    }),
  );
}

export async function updateUser(
  userId: number,
  patch: { password?: string; is_admin?: boolean; is_active?: boolean },
): Promise<User> {
  return handle(
    await fetch(`${BASE}/api/users/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),
  );
}

export async function deleteUser(userId: number): Promise<void> {
  await handle(await fetch(`${BASE}/api/users/${userId}`, { method: "DELETE" }));
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

/** 告诉后端「当前书」，保证对话引擎与前端显示一致。 */
export async function selectBook(bookId: number): Promise<void> {
  await handle(
    await fetch(`${BASE}/api/books/${bookId}/select`, { method: "POST" }),
  );
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