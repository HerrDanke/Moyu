import { useEffect, useRef } from "react";
import type { Book, ReadingMode, Theme, User } from "../types";
import { Logo } from "./Logo";

interface Props {
  books: Book[];
  currentId: number | null;
  /** 每本书已读到的章节号 */
  progressByBook: Record<number, number>;
  onSelect: (id: number) => void;
  onImport: (file: File) => void;
  onDelete: (id: number) => void;
  busy?: boolean;
  /** 当前书进度文案，如「第 1 / 1807 章 · 本章 42%」 */
  progressLabel: string | null;
  theme: Theme;
  onToggleTheme: () => void;
  quickRead: boolean;
  onToggleQuickRead: () => void;
  readingMode: ReadingMode;
  onToggleReadingMode: () => void;
  onLogout: () => void;
  open: boolean;
  onClose: () => void;
  currentUser: User;
  onOpenUserAdmin: () => void;
}

export function Sidebar({
  books,
  currentId,
  progressByBook,
  onSelect,
  onImport,
  onDelete,
  busy,
  progressLabel,
  theme,
  onToggleTheme,
  quickRead,
  onToggleQuickRead,
  readingMode,
  onToggleReadingMode,
  onLogout,
  open,
  onClose,
  currentUser,
  onOpenUserAdmin,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLElement>(null);

  // 抽屉：Esc 关闭 + 焦点陷阱（窄屏时才有视觉意义，逻辑常驻无害）
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const focusables = panel.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      {open && <div className="sidebar-scrim" onClick={onClose} aria-hidden="true" />}
      <aside
        ref={panelRef}
        className={`sidebar${open ? " is-open" : ""}`}
        data-testid="sidebar"
        role={open ? "dialog" : undefined}
        aria-modal={open || undefined}
        aria-label="书架与设置"
      >
        <div className="sidebar-head">
          <span className="brand" data-testid="brand">
            <Logo size={20} />
            <span className="brand-name">墨鱼</span>
          </span>
          <button
            type="button"
            className="icon-btn sidebar-close"
            onClick={onClose}
            aria-label="关闭侧栏"
          >
            ✕
          </button>
        </div>

        <input
          ref={fileRef}
          data-testid="import-input"
          type="file"
          accept=".txt,text/plain"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onImport(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="sidebar-action"
          data-testid="import-button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          ＋ 导入新书
        </button>

        <p className="sidebar-label">我的书架</p>
        <nav className="shelf" data-testid="book-list">
          {books.length === 0 && <p className="shelf-empty">还没有书，先导入一本试试</p>}
          {books.map((b) => (
            <div
              key={b.id}
              className={`shelf-item${b.id === currentId ? " is-current" : ""}`}
              data-testid={`book-item-${b.id}`}
            >
              <button
                type="button"
                className="shelf-btn"
                aria-current={b.id === currentId || undefined}
                onClick={() => onSelect(b.id)}
              >
                <span className="shelf-title">{b.title}</span>
                <span className="shelf-meta">
                  第 {progressByBook[b.id] ?? 1} / {b.total_chapters} 章
                </span>
              </button>
              <button
                type="button"
                className="icon-btn shelf-del"
                data-testid={`book-delete-${b.id}`}
                title="删除这本书"
                aria-label={`删除《${b.title}》`}
                onClick={() => {
                  if (confirm(`确定删除《${b.title}》吗？`)) onDelete(b.id);
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          {progressLabel && (
            <p className="sidebar-progress" data-testid="sidebar-progress">
              {progressLabel}
            </p>
          )}
          <button
            type="button"
            className="sidebar-toggle-row"
            data-testid="reading-mode-toggle"
            aria-pressed={readingMode === "wide"}
            onClick={onToggleReadingMode}
          >
            <span>宽松排版</span>
            <span className="toggle-pill">{readingMode === "wide" ? "开" : "关"}</span>
          </button>
          <button
            type="button"
            className="sidebar-toggle-row"
            data-testid="quick-read-toggle"
            aria-pressed={quickRead}
            onClick={onToggleQuickRead}
          >
            <span>快速阅读</span>
            <span className="toggle-pill">{quickRead ? "开" : "关"}</span>
          </button>
          <button
            type="button"
            className="sidebar-toggle-row"
            data-testid="theme-toggle"
            aria-pressed={theme === "dark"}
            onClick={onToggleTheme}
          >
            <span>深色主题</span>
            <span className="toggle-pill">{theme === "dark" ? "开" : "关"}</span>
          </button>
          {currentUser.is_admin && (
            <button
              type="button"
              className="sidebar-toggle-row"
              data-testid="user-admin-entry"
              onClick={onOpenUserAdmin}
            >
              <span>用户管理</span>
            </button>
          )}
          <div className="sidebar-user" data-testid="sidebar-user">
            <span className="user-name">
              {currentUser.username}
              {currentUser.is_admin && <span className="tag">管理员</span>}
            </span>
            <button
              type="button"
              className="link-btn"
              data-testid="logout-button"
              onClick={onLogout}
            >
              退出登录
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}