import { useEffect, useRef } from "react";
import type { AppSettings, ReadingMode, Theme } from "../types";

interface Props {
  onClose: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  readingMode: ReadingMode;
  onToggleReadingMode: () => void;
  quickRead: boolean;
  onToggleQuickRead: () => void;
  onLogout: () => void;
  settings: AppSettings | null;
  onSelectLevel: (level: number) => void;
  saving: boolean;
}

export function SettingsDialog({
  onClose,
  theme,
  onToggleTheme,
  readingMode,
  onToggleReadingMode,
  quickRead,
  onToggleQuickRead,
  onLogout,
  settings,
  onSelectLevel,
  saving,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Esc 关闭 + 焦点陷阱（与用户管理对话框一致）
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

  const levels = settings?.levels ?? [];
  const currentLevel = settings?.thinking_level ?? null;
  const current = levels.find((l) => l.level === currentLevel);

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div
        className="modal settings-modal"
        data-testid="settings-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="设置"
        ref={panelRef}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-head">
          <h2>设置</h2>
          <button
            type="button"
            className="icon-btn"
            data-testid="settings-close"
            aria-label="关闭设置"
            onClick={onClose}
          >
            ✕
          </button>
        </header>

        <section className="setting-block">
          <div className="setting-title">
            <span>思考强度</span>
            <span className="setting-value" data-testid="thinking-label">
              {current ? current.name : "—"}
            </span>
          </div>
          <input
            data-testid="thinking-slider"
            className="thinking-slider"
            type="range"
            min={1}
            max={Math.max(levels.length, 4)}
            step={1}
            value={currentLevel ?? 2}
            disabled={!settings || saving}
            aria-label="思考强度"
            aria-valuetext={current?.name}
            onChange={(e) => onSelectLevel(Number(e.target.value))}
          />
          <div className="slider-ticks">
            {levels.map((l) => (
              <span key={l.level} className={l.level === currentLevel ? "is-active" : ""}>
                {l.name}
              </span>
            ))}
          </div>
          <p className="setting-hint">
            {current ? current.hint : "调整后影响正文逐字出现的节奏"}
            {settings && !settings.typing_speed_from_user && "（当前沿用服务端默认）"}
          </p>
        </section>

        <section className="setting-block">
          <p className="modal-label">阅读与外观</p>
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
        </section>

        <section className="setting-block">
          <button
            type="button"
            className="sidebar-toggle-row danger-row"
            data-testid="logout-button"
            onClick={onLogout}
          >
            <span>退出登录</span>
          </button>
        </section>
      </div>
    </div>
  );
}