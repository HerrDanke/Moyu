import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  deleteBook,
  getAuthStatus,
  getChapters,
  getProgress,
  getSettings,
  importBook,
  listBooks,
  login,
  logout,
  onUnauthorized,
  patchProgress,
  patchSettings,
  selectBook,
  setup as setupAccount,
  streamChat,
} from "./api/client";
import type {
  AppSettings,
  Book,
  ChapterMeta,
  ChatMessage,
  Progress,
  ReadingMode,
  Theme,
  User,
} from "./types";
import { MessageList } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { ReadingToolbar } from "./components/ReadingToolbar";
import { ChapterDrawer } from "./components/ChapterDrawer";
import { Sidebar } from "./components/Sidebar";
import { EmptyState } from "./components/EmptyState";
import { LoginPage } from "./components/LoginPage";
import { SetupPage } from "./components/SetupPage";
import { SettingsDialog } from "./components/SettingsDialog";
import { UserAdminDialog } from "./components/UserAdminDialog";
import { newId } from "./utils/id";
import { formatProgressLabel } from "./utils/progress";

const THEME_KEY = "moyu_theme";
const BOOK_KEY = "moyu_current_book";
const READING_KEY = "moyu_reading_mode";

type AuthState = "checking" | "setup" | "login" | "ok";

export default function App() {
  const [auth, setAuth] = useState<AuthState>("checking");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [userAdminOpen, setUserAdminOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [progressMap, setProgressMap] = useState<Record<number, Progress>>({});
  const [chapters, setChapters] = useState<ChapterMeta[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [quickRead, setQuickRead] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tocOpen, setTocOpen] = useState(false);
  // 草稿提升到这里：手输与「跳转章节」的预填共用同一份真相
  const [draft, setDraft] = useState("");
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(THEME_KEY) as Theme) || "light",
  );
  const [readingMode, setReadingMode] = useState<ReadingMode>(
    () => (localStorage.getItem(READING_KEY) as ReadingMode) || "wide",
  );

  const abortRef = useRef<(() => void) | null>(null);
  const lastPatchRef = useRef(0);
  const messagesRef = useRef<ChatMessage[]>([]);
  const currentIdRef = useRef<number | null>(null);
  // 只有「当前正在阅读的这条消息」允许上报偏移：
  // 上一章的打字机在流式结束后还会继续跑几十秒，若不拦住，
  // 它会把新章节的偏移覆盖成旧章节的位置。
  const activeMsgIdRef = useRef<string | null>(null);

  messagesRef.current = messages;
  currentIdRef.current = currentId;

  const progress = currentId != null ? (progressMap[currentId] ?? null) : null;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.dataset.reading = readingMode;
    localStorage.setItem(READING_KEY, readingMode);
  }, [readingMode]);

  useEffect(() => {
    onUnauthorized(() => {
      setCurrentUser(null);
      setAuth("login");
    });
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const s = await getAuthStatus();
        if (s.setup_required) {
          setAuth("setup");
          return;
        }
        if (s.authenticated && s.user) {
          setCurrentUser(s.user);
          setAuth("ok");
          try {
            setAppSettings(await getSettings());
          } catch {
            /* 设置拉取失败不阻塞进入 */
          }
        } else {
          setAuth("login");
        }
      } catch {
        setAuth("login");
      }
    })();
  }, []);

  /** 拉取所有书的进度，用于侧栏每本书的进度标签 */
  const loadAllProgress = useCallback(async (list: Book[]) => {
    const results = await Promise.all(
      list.map(async (b) => {
        try {
          return [b.id, await getProgress(b.id)] as const;
        } catch {
          return null;
        }
      }),
    );
    const map: Record<number, Progress> = {};
    for (const r of results) if (r) map[r[0]] = r[1];
    setProgressMap(map);
  }, []);

  useEffect(() => {
    if (auth !== "ok") return;
    (async () => {
      const list = await listBooks();
      setBooks(list);
      void loadAllProgress(list);
      const saved = Number(localStorage.getItem(BOOK_KEY));
      const initial = list.find((b) => b.id === saved)?.id ?? list[0]?.id ?? null;
      setCurrentId(initial);
      if (initial != null) void selectBook(initial).catch(() => {});
    })();
  }, [auth, loadAllProgress]);

  useEffect(() => {
    if (currentId == null) {
      setChapters([]);
      return;
    }
    (async () => {
      try {
        setChapters(await getChapters(currentId));
      } catch {
        setChapters([]);
      }
    })();
  }, [currentId]);

  const handleLogin = async (username: string, password: string) => {
    setLoginError(null);
    try {
      const user = await login(username, password);
      setCurrentUser(user);
      setAuth("ok");
      try {
        setAppSettings(await getSettings());
      } catch {
        /* ignore */
      }
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "登录失败");
    }
  };

  /** 选择「思考强度」档位：把服务端给的档位速度发回去，立即用于下一次阅读。 */
  const handleSelectLevel = useCallback(
    async (level: number) => {
      const option = appSettings?.levels.find((l) => l.level === level);
      if (!option) return;
      setSavingSettings(true);
      try {
        setAppSettings(await patchSettings(option.speed));
      } catch {
        /* 失败就保留原值 */
      } finally {
        setSavingSettings(false);
      }
    },
    [appSettings],
  );

  const handleSetup = async (username: string, password: string, setupCode: string) => {
    setLoginError(null);
    try {
      const user = await setupAccount(username, password, setupCode);
      setCurrentUser(user);
      setAuth("ok");
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
    setAuth("login");
    setMessages([]);
    setSettingsOpen(false);
    setUserAdminOpen(false);
  };

  /** 切书 = 开新会话：清空消息区并进入该书的空状态。 */
  const chooseBook = useCallback((id: number | null) => {
    setCurrentId(id);
    setMessages([]);
    setSidebarOpen(false);
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
      void loadAllProgress(list);
      setCurrentId(res.book_id);
      localStorage.setItem(BOOK_KEY, String(res.book_id));
      // 必须同步服务端「当前书」，否则「下一章」会读到上一本
      void selectBook(res.book_id).catch(() => {});
      setSidebarOpen(false);
      setMessages([
        {
          id: newId(),
          role: "assistant",
          text: `已导入《${res.title}》，共 ${res.total_chapters} 章。${
            res.notice ? res.notice + "。" : ""
          }说「下一章」开始阅读。`,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: newId(),
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
      void loadAllProgress(list);
      chooseBook(list[0]?.id ?? null);
    } finally {
      setBusy(false);
    }
  };

  const refreshProgressOf = useCallback(async (bookId: number) => {
    try {
      const p = await getProgress(bookId);
      setProgressMap((prev) => ({ ...prev, [bookId]: p }));
    } catch {
      /* ignore */
    }
  }, []);

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = { id: newId(), role: "user", text };
    const asstId = newId();
    const asstMsg: ChatMessage = { id: asstId, role: "assistant", text: "", streaming: true };
    setMessages((m) => [...m, userMsg, asstMsg]);
    setStreaming(true);
    activeMsgIdRef.current = asstId;

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
            case "book": {
              const changed = ev.id !== currentIdRef.current;
              setCurrentId(ev.id);
              localStorage.setItem(BOOK_KEY, String(ev.id));
              update({ bookId: ev.id });
              if (changed) {
                // 通过指令切书同样视为新会话：丢掉旧书的消息，只保留本次指令与回复
                setMessages((m) =>
                  m.filter((msg) => msg.id === asstId || msg.id === userMsg.id),
                );
              }
              break;
            }
            case "meta":
              update((prev) => ({
                ...prev,
                startOffset: ev.start_offset,
                charCount: ev.char_count,
                chapterIndex: ev.chapter_index,
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
      const id = currentIdRef.current;
      if (id != null) await refreshProgressOf(id);
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

  const handleStop = () => {
    abortRef.current?.();
    setStreaming(false);
    setMessages((m) => m.map((msg) => (msg.streaming ? { ...msg, streaming: false } : msg)));
  };

  /** 「跳转章节」：预填输入框并聚焦，不发请求 —— 复用既有的「第 N 章」指令。 */
  const handleJump = useCallback(() => {
    setDraft("第 ");
    requestAnimationFrame(() => {
      const el = composerRef.current;
      if (!el) return;
      el.focus();
      const len = el.value.length;
      el.setSelectionRange(len, len);
    });
  }, []);

  /** 目录里点某一章：走既有指令，进度与流式输出都由原逻辑负责。 */
  const handlePickChapter = useCallback(
    (chapterIndex: number) => {
      setTocOpen(false);
      void handleSend(`第 ${chapterIndex} 章`);
    },
    // handleSend 每次渲染都会重建，这里用 ref 之外的简单方式：允许依赖它
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  /** 上报续读偏移：只按章节正文字符数计算，并把服务端返回的进度回写本地。 */
  const handleProgressReport = useCallback((messageId: string, revealed: number) => {
    // 只认当前活跃消息：旧章节的滞留打字机不得写入进度
    if (messageId !== activeMsgIdRef.current) return;
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
    void patchProgress(bookId, { chapter_offset: offset })
      .then((updated) => {
        setProgressMap((prev) => ({ ...prev, [updated.book_id]: updated }));
      })
      .catch(() => {});
  }, []);

  const currentBook = useMemo(
    () => books.find((b) => b.id === currentId) ?? null,
    [books, currentId],
  );

  const currentChapterChars = useMemo(() => {
    if (!progress) return 0;
    return chapters.find((c) => c.index_no === progress.chapter_index)?.char_count ?? 0;
  }, [chapters, progress]);

  const progressLabel = useMemo(() => {
    if (!currentBook || !progress) return null;
    return formatProgressLabel(
      progress.chapter_index,
      currentBook.total_chapters,
      progress.chapter_offset,
      currentChapterChars,
    );
  }, [currentBook, progress, currentChapterChars]);

  const progressByBook = useMemo(() => {
    const map: Record<number, number> = {};
    for (const [id, p] of Object.entries(progressMap)) map[Number(id)] = p.chapter_index;
    return map;
  }, [progressMap]);

  if (auth === "checking") return <div className="loading">加载中…</div>;
  if (auth === "setup") return <SetupPage onSubmit={handleSetup} error={loginError} />;
  if (auth === "login" || !currentUser)
    return <LoginPage onSubmit={handleLogin} error={loginError} />;

  const isEmpty = messages.length === 0;

  return (
    <div className="shell">
      <Sidebar
        books={books}
        currentId={currentId}
        progressByBook={progressByBook}
        onSelect={chooseBook}
        onImport={handleImport}
        onDelete={handleDelete}
        busy={busy}
        progressLabel={progressLabel}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentUser={currentUser}
        onOpenUserAdmin={() => setUserAdminOpen(true)}
        onOpenSettings={() => {
          setSidebarOpen(false);
          setSettingsOpen(true);
        }}
      />

      {settingsOpen && (
        <SettingsDialog
          onClose={() => setSettingsOpen(false)}
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          readingMode={readingMode}
          onToggleReadingMode={() =>
            setReadingMode((m) => (m === "wide" ? "compact" : "wide"))
          }
          quickRead={quickRead}
          onToggleQuickRead={() => setQuickRead((q) => !q)}
          onLogout={handleLogout}
          settings={appSettings}
          onSelectLevel={handleSelectLevel}
          saving={savingSettings}
        />
      )}

      {userAdminOpen && currentUser.is_admin && (
        <UserAdminDialog
          currentUser={currentUser}
          onClose={() => setUserAdminOpen(false)}
        />
      )}

      <main className={`main${isEmpty ? " is-empty" : ""}`}>
        <button
          type="button"
          className="icon-btn sidebar-open"
          data-testid="sidebar-toggle"
          aria-label="打开侧栏"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          ☰
        </button>

        {isEmpty ? (
          currentBook && progress ? (
            <EmptyState
              bookTitle={currentBook.title}
              chapterIndex={progress.chapter_index}
              totalChapters={currentBook.total_chapters}
            />
          ) : (
            <div className="empty-state" data-testid="empty-state">
              <h1 className="empty-title">还没有书</h1>
              <p className="empty-sub">从左侧「导入新书」添加一本 TXT 小说</p>
            </div>
          )
        ) : (
          <MessageList
            messages={messages}
            animate={!quickRead}
            onProgress={handleProgressReport}
          />
        )}

        <div className="composer-wrap">
          <ReadingToolbar
            sendingDisabled={streaming}
            onSend={handleSend}
            onOpenToc={() => setTocOpen(true)}
            onJump={handleJump}
          />
          <Composer
            streaming={streaming}
            draft={draft}
            onDraftChange={setDraft}
            onSend={handleSend}
            onStop={handleStop}
            inputRef={composerRef}
          />
        </div>
      </main>

      {tocOpen && (
        <ChapterDrawer
          bookId={currentId}
          bookTitle={currentBook?.title ?? ""}
          currentIndex={progress?.chapter_index ?? null}
          onPick={handlePickChapter}
          onClose={() => setTocOpen(false)}
        />
      )}
    </div>
  );
}