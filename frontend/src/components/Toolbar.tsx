interface Props {
  theme: "light" | "dark";
  onToggleTheme: () => void;
  quickRead: boolean;
  onToggleQuickRead: () => void;
  onLogout?: () => void;
}

export function Toolbar({
  theme,
  onToggleTheme,
  quickRead,
  onToggleQuickRead,
  onLogout,
}: Props) {
  return (
    <div className="toolbar">
      <label className="toggle">
        <input type="checkbox" checked={quickRead} onChange={onToggleQuickRead} />
        <span>快速阅读</span>
      </label>
      <button className="btn ghost" onClick={onToggleTheme}>
        {theme === "dark" ? "浅色" : "深色"}
      </button>
      {onLogout && (
        <button className="btn ghost" onClick={onLogout}>
          退出
        </button>
      )}
    </div>
  );
}