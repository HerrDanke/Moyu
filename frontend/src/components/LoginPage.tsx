import { useState } from "react";
import { Logo } from "./Logo";

interface Props {
  onSubmit: (username: string, password: string) => void;
  error: string | null;
}

export function LoginPage({ onSubmit, error }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="login-page">
      <form
        className="login-card"
        onSubmit={(e) => {
          e.preventDefault();
          if (username && password) onSubmit(username, password);
        }}
      >
        <div className="login-brand">
          <Logo size={26} />
          <h1>墨鱼</h1>
        </div>
        <p className="subtitle">登录后继续阅读</p>
        <input
          data-testid="login-username"
          type="text"
          value={username}
          placeholder="用户名"
          autoComplete="username"
          autoFocus
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          data-testid="login-password"
          type="password"
          value={password}
          placeholder="密码"
          autoComplete="current-password"
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <button className="btn" data-testid="login-submit" type="submit">
          进入
        </button>
      </form>
    </div>
  );
}