import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  deleteBook,
  getAuthStatus,
  getChapters,
  getProgress,
  importBook,
  listBooks,
  login,
  logout,
  onUnauthorized,
  patchProgress,
  selectBook,
  streamChat,
} from "./api/client";
import type { Book, ChapterMeta, ChatMessage, Progress } from "./types";
import { MessageList } from "./components/MessageList";
import { ChatInput } from "./components/ChatInput";
import { BookSelector } from "./components/BookSelector";
import { ChapterProgress } from "./components/ChapterProgress";
import { LoginPage } from "./components/LoginPage";
import { Toolbar } from "./components/Toolbar";

const THEME_KEY = "moyu_theme";
const BOOK_KEY = "moyu_current_book";

type AuthState = "checking" | "login" | "ok";

export default function App() {
  const [auth, setAuth] = useState<AuthState>("checking");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [chapters, setChapters] = useState<ChapterMeta[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [quickRead, setQuickRead] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem(THEME_KEY) as "light" | "dark") || "light",
  );

  const abortRef = useRef<(() => void) | null>(null);
  const lastPatchRef = useRef(0);
  const messagesRef = useRef<ChatMessage[]>([]);
  const currentIdRef = useRef<number | null>(null);

  messagesRef.current = messages;
  currentIdRef.current = currentId;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  // 会话过期时回到登录页
  useEffect(() => {
    onUnauthorized(() => setAuth("login"));
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const s = await getAuthStatus();
        setAuth(s.authenticated ? "ok" : "login");
      } catch {
        setAuth("login");
      }
    })();
  }, []);

  useEffect(() => {
    if (auth !== "ok") return;
    (async () => {
      const list = await listBooks();
      setBooks(list);
      const saved = Number(localStorage.getItem(BOOK_KEY));
      const initial = list.find((b) => b.id === saved)?.id ?? list[0]?.id ?? null;
      setCurrentId(initial);
      if (initial != null) void selectBook(initial).catch(() => {});
    })();
  }, [auth]);

  useEffect(() => {
    if (currentId == null) {
      setProgress(null);
      setChapters([]);
      return;
    }
    (async () => {
      const [p, cs] = await Promise.all([getProgress(currentId), getChapters(currentId)]);
      setProgress(p);
      setChapters(cs);
    })();
  }, [currentId]);

  const refreshProgress = useCallback(async (id: number | null) => {
    if (id == null) return;
    try {
      setProgress(await getProgress(id));
    } catch {
      /* ignore */
    }
  }, []);

  const handleLogin = async (password: string) => {
    setLoginError(null);
    try {
      await login(password);
      setAuth("ok");
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "登录失败");
    }
  };

  const handleLogout = async () => {
    await logout();
    setAuth("login");
    setMessages([]);
  };

  /** 切换当前书：同时同步到后端，保证对话引擎与界面一致。 */
  const chooseBook = useCallback((id: number | null) => {
    setCurrentId(id);
    if (id != null) {
      localStorage.setItem(BOOK_KEY, String(id));
      void selectBook(id).catch(() => {});
    }
  }, []);

  const handleImport = async (file: File) => {
    setBusy(true);
    try {
      const res = await importBook(file);
      const list = await listBooks();
      setBooks(list);
      chooseBook(res.book_id);
      setMessages([
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `已导入《${res.title}》，共 ${res.total_chapters} 章。${
            res.notice ? res.notice + "。" : ""
          }回复「下一章」开始阅读。`,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `导入失败：${e instanceof Error ? e.message : "未知错误"}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: number) => {
    setBusy(true);
    try {
      await deleteBook(id);
      const list = await listBooks();
      setBooks(list);
      chooseBook(list[0]?.id ?? null);
      setMessages([]);
    } finally {
      setBusy(false);
    }
  };

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    const asstId = crypto.randomUUID();
    const asstMsg: ChatMessage = { id: asstId, role: "assistant", text: "", streaming: true };
    setMessages((m) => [...m, userMsg, asstMsg]);
    setStreaming(true);

    const update = (patch: Partial<ChatMessage> | ((prev: ChatMessage) => ChatMessage)) => {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === asstId
            ? typeof patch === "function"
              ? patch(msg)
              : { ...msg, ...patch }
            : msg,
        ),
      );
    };

    try {
      const { abort, done } = streamChat(
        text,
        (ev) => {
          switch (ev.type) {
            case "book":
              // 服务端认定的「当前书」可能与前端不同（例如「读《x》」）
              setCurrentId(ev.id);
              localStorage.setItem(BOOK_KEY, String(ev.id));
              update({ bookId: ev.id });
              break;
            case "meta":
              update((prev) => ({
                ...prev,
                startOffset: ev.start_offset,
                charCount: ev.char_count,
              }));
              break;
            case "thinking":
              update((prev) => ({ ...prev, thinking: ev.text }));
              break;
            case "title":
              update((prev) => ({
                ...prev,
                text: ev.text + "\n\n",
                bodyStart: ev.text.length + 2,
                thinking: undefined,
              }));
              break;
            case "chunk":
              update((prev) => ({ ...prev, text: prev.text + ev.text, thinking: undefined }));
              break;
            case "footer":
              update((prev) => ({ ...prev, text: prev.text + "\n\n" + ev.text }));
              break;
            case "done":
              update({ streaming: false });
              break;
          }
        },
        { quickRead },
      );
      abortRef.current = abort;
      await done;
      update({ streaming: false });
      await refreshProgress(currentIdRef.current);
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        update({ streaming: false });
      } else {
        update({ streaming: false, text: `出错了：${(e as Error).message}` });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const handleSkip = () => {
    abortRef.current?.();
    setStreaming(false);
    setMessages((m) => m.map((msg) => (msg.streaming ? { ...msg, streaming: false } : msg)));
  };

  /**
   * 上报续读偏移：只按「章节正文字符数」计算，剔除标题与收尾文案，
   * 且只在该消息所属书 == 当前书时才上报。
   */
  const handleProgressReport = useCallback((messageId: string, revealed: number) => {
    const msg = messagesRef.current.find((m) => m.id === messageId);
    if (!msg || msg.startOffset === undefined || msg.charCount === undefined) return;
    const bookId = msg.bookId ?? currentIdRef.current;
    if (bookId == null || bookId !== currentIdRef.current) return;

    const bodyStart = msg.bodyStart ?? 0;
    const bodyLen = Math.max(0, msg.charCount - msg.startOffset);
    const revealedBody = Math.max(0, Math.min(revealed - bodyStart, bodyLen));
    if (revealedBody <= 0) return;

    const now = Date.now();
    if (now - lastPatchRef.current < 1000) return;
    lastPatchRef.current = now;
    const offset = msg.startOffset + revealedBody;
    void patchProgress(bookId, { chapter_offset: offset }).catch(() => {});
  }, []);

  const currentBook = useMemo(
    () => books.find((b) => b.id === currentId) ?? null,
    [books, currentId],
  );

  const currentChapterChars = useMemo(() => {
    if (!progress) return 0;
    return chapters.find((c) => c.index_no === progress.chapter_index)?.char_count ?? 0;
  }, [chapters, progress]);

  if (auth === "checking") return <div className="loading">加载中…</div>;
  if (auth === "login") return <LoginPage onSubmit={handleLogin} error={loginError} />;

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="logo">墨鱼</span>
          {currentBook && progress && (
            <ChapterProgress
              bookTitle={currentBook.title}
              chapterIndex={progress.chapter_index}
              totalChapters={currentBook.total_chapters}
              offset={progress.chapter_offset}
              chapterChars={currentChapterChars}
            />
          )}
        </div>
        <Toolbar
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          quickRead={quickRead}
          onToggleQuickRead={() => setQuickRead((q) => !q)}
          onLogout={handleLogout}
        />
      </header>

      <div className="book-bar">
        <BookSelector
          books={books}
          currentId={currentId}
          onSelect={chooseBook}
          onImport={handleImport}
          onDelete={handleDelete}
          busy={busy}
        />
      </div>

      <main className="chat-area">
        <MessageList
          messages={messages}
          animate={!quickRead}
          onProgress={handleProgressReport}
        />
      </main>

      <ChatInput streaming={streaming} onSend={handleSend} onSkip={handleSkip} />
    </div>
  );
}