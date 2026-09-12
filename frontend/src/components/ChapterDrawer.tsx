import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "../api/client";
import type { ChapterMeta } from "../types";

const ROW_HEIGHT = 32;
const OVERSCAN = 8;

interface Props {
  bookId: number | null;
  bookTitle: string;
  currentIndex: number | null;
  onPick: (chapterIndex: number) => void;
  onClose: () => void;
}

/**
 * 章节目录抽屉。
 *
 * 书可能有上千章（例如 1807 章），因此做**轻量窗口化**：只渲染可视区域附近的行，
 * 用一个总高度占位元素撑开滚动条。行高固定，索引计算是 O(1)，不引入虚拟列表库。
 */
export function ChapterDrawer({
  bookId,
  bookTitle,
  currentIndex,
  onPick,
  onClose,
}: Props) {
  const [chapters, setChapters] = useState<ChapterMeta[]>([]);
  const [query, setQuery] = useState("");
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportH, setViewportH] = useState(520);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bookId == null) return;
    let alive = true;
    setLoading(true);
    api
      .getChapters(bookId)
      .then((list) => {
        if (!alive) return;
        setChapters(list);
        setError(null);
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : "目录加载失败");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [bookId]);

  // Esc 关闭 + 焦点陷阱
  useEffect(() => {
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
  }, [onClose]);

  // 测量可视高度（用于窗口化）
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const update = () => setViewportH(el.clientHeight || 520);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [loading]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return chapters;
    return chapters.filter(
      (c) => c.title.toLowerCase().includes(q) || String(c.index_no) === q,
    );
  }, [chapters, query]);

  // 打开（或清空搜索）后定位到当前章
  useEffect(() => {
    if (query || !chapters.length || currentIndex == null) return;
    const pos = chapters.findIndex((c) => c.index_no === currentIndex);
    const el = listRef.current;
    if (pos < 0 || !el) return;
    el.scrollTop = Math.max(
      0,
      pos * ROW_HEIGHT - el.clientHeight / 2 + ROW_HEIGHT / 2,
    );
    setScrollTop(el.scrollTop);
  }, [chapters, currentIndex, query]);

  const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const windowSize = Math.ceil(viewportH / ROW_HEIGHT) + OVERSCAN * 2;
  const end = Math.min(filtered.length, start + windowSize);
  const slice = filtered.slice(start, end);

  return (
    <div className="drawer-scrim" onClick={onClose}>
      <div
        className="drawer"
        data-testid="toc-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="章节目录"
        ref={panelRef}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="drawer-head">
          <h2 title={bookTitle}>{bookTitle || "目录"} · 目录</h2>
          <button
            type="button"
            className="icon-btn"
            data-testid="toc-close"
            aria-label="关闭目录"
            onClick={onClose}
          >
            ✕
          </button>
        </header>

        <input
          data-testid="toc-search"
          className="drawer-search"
          type="text"
          placeholder="搜索章节标题或章号…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <div
          className="drawer-list"
          ref={listRef}
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
        >
          {bookId == null && <p className="drawer-hint">还没有选定书籍</p>}
          {loading && <p className="drawer-hint">目录加载中…</p>}
          {error && <p className="error">{error}</p>}
          {bookId != null && !loading && !error && filtered.length === 0 && (
            <p className="drawer-hint">
              {chapters.length === 0 ? "这本书没有章节" : "没有匹配的章节"}
            </p>
          )}

          {filtered.length > 0 && (
            <div className="drawer-spacer" style={{ height: filtered.length * ROW_HEIGHT }}>
              <div
                className="drawer-window"
                style={{ transform: `translateY(${start * ROW_HEIGHT}px)` }}
              >
                {slice.map((c) => {
                  const isCurrent = c.index_no === currentIndex;
                  return (
                    <button
                      key={c.index_no}
                      type="button"
                      className={`toc-item${isCurrent ? " is-current" : ""}`}
                      data-testid={`toc-item-${c.index_no}`}
                      aria-current={isCurrent || undefined}
                      onClick={() => onPick(c.index_no)}
                    >
                      <span className="toc-no">{c.index_no}</span>
                      <span className="toc-title">{c.title}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}