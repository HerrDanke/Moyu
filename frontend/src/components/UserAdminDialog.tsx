import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api/client";
import type { User } from "../types";

interface Props {
  currentUser: User;
  onClose: () => void;
}

/** 管理员用户管理对话框：列表 / 新建 / 重置密码 / 切换管理员 / 启停 / 删除。 */
export function UserAdminDialog({ currentUser, onClose }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const reload = useCallback(async () => {
    try {
      setUsers(await api.listUsers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

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

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    setBusy(true);
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const create = () =>
    run(async () => {
      await api.createUser(newName.trim(), newPassword, newIsAdmin);
      setNewName("");
      setNewPassword("");
      setNewIsAdmin(false);
    });

  const resetPassword = (u: User) => {
    const pwd = window.prompt(`为「${u.username}」设置新密码（至少 4 位）`);
    if (!pwd) return;
    void run(() => api.updateUser(u.id, { password: pwd }));
  };

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div
        className="modal"
        data-testid="user-admin-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="用户管理"
        ref={panelRef}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-head">
          <h2>用户管理</h2>
          <button
            type="button"
            className="icon-btn"
            data-testid="user-admin-close"
            aria-label="关闭"
            onClick={onClose}
          >
            ✕
          </button>
        </header>

        {error && <p className="error">{error}</p>}

        <ul className="user-list" data-testid="user-list">
          {users.map((u) => (
            <li key={u.id} className="user-row" data-testid={`user-row-${u.id}`}>
              <span className="user-name">
                {u.username}
                {u.id === currentUser.id && <em className="user-self">（我）</em>}
              </span>
              <span className="user-tags">
                {u.is_admin && <span className="tag">管理员</span>}
                {!u.is_active && <span className="tag tag-off">已停用</span>}
              </span>
              <span className="user-actions">
                <button
                  type="button"
                  className="link-btn"
                  disabled={busy}
                  onClick={() => resetPassword(u)}
                >
                  重置密码
                </button>
                <button
                  type="button"
                  className="link-btn"
                  data-testid={`toggle-admin-${u.id}`}
                  disabled={busy}
                  onClick={() => void run(() => api.updateUser(u.id, { is_admin: !u.is_admin }))}
                >
                  {u.is_admin ? "取消管理员" : "设为管理员"}
                </button>
                <button
                  type="button"
                  className="link-btn"
                  disabled={busy}
                  onClick={() => void run(() => api.updateUser(u.id, { is_active: !u.is_active }))}
                >
                  {u.is_active ? "停用" : "启用"}
                </button>
                <button
                  type="button"
                  className="link-btn danger"
                  data-testid={`delete-user-${u.id}`}
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm(`确定删除用户「${u.username}」吗？其阅读进度会一并清除。`)) {
                      void run(() => api.deleteUser(u.id));
                    }
                  }}
                >
                  删除
                </button>
              </span>
            </li>
          ))}
        </ul>

        <div className="user-create">
          <p className="modal-label">新建用户</p>
          <div className="user-create-row">
            <input
              data-testid="new-user-name"
              type="text"
              placeholder="用户名"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <input
              data-testid="new-user-password"
              type="password"
              placeholder="密码（≥4 位）"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <label className="checkbox">
              <input
                type="checkbox"
                checked={newIsAdmin}
                onChange={(e) => setNewIsAdmin(e.target.checked)}
              />
              管理员
            </label>
            <button
              type="button"
              className="btn"
              data-testid="create-user-submit"
              disabled={busy || !newName.trim() || !newPassword}
              onClick={create}
            >
              创建
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}