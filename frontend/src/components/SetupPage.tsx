import { useState } from "react";
import { Logo } from "./Logo";

interface Props {
  onSubmit: (username: string, password: string, setupCode: string) => void;
  error: string | null;
}

/**
 * 首次运行引导：创建第一个管理员。
 * 引导口令只出现在服务器启动日志里，因此只有拥有服务器访问权的人能完成。
 */
export function SetupPage({ onSubmit, error }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [setupCode, setSetupCode] = useState("");

  return (
    <div className="login-page">
      <form
        className="login-card"
        onSubmit={(e) => {
          e.preventDefault();
          if (username && password && setupCode) onSubmit(username, password, setupCode);
        }}
      >
        <div className="login-brand">
          <Logo size={26} />
          <h1>墨鱼</h1>
        </div>
        <p className="subtitle">首次使用：创建管理员账号</p>
        <input
          data-testid="setup-username"
          type="text"
          value={username}
          placeholder="管理员用户名"
          autoComplete="username"
          autoFocus
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          data-testid="setup-password"
          type="password"
          value={password}
          placeholder="密码（至少 4 位）"
          autoComplete="new-password"
          onChange={(e) => setPassword(e.target.value)}
        />
        <input
          data-testid="setup-code"
          type="text"
          value={setupCode}
          placeholder="引导口令"
          onChange={(e) => setSetupCode(e.target.value)}
        />
        <p className="hint">
          引导口令在服务端启动日志里（形如 <code>XXXXX-XXXXX-XXXXX-XXXXX</code>）
        </p>
        {error && <p className="error">{error}</p>}
        <button className="btn" data-testid="setup-submit" type="submit">
          创建并进入
        </button>
      </form>
    </div>
  );
}