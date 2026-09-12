import { useState } from "react";

interface Props {
  onSubmit: (password: string) => void;
  error: string | null;
}

export function LoginPage({ onSubmit, error }: Props) {
  const [password, setPassword] = useState("");

  return (
    <div className="login-page">
      <form
        className="login-card"
        onSubmit={(e) => {
          e.preventDefault();
          if (password) onSubmit(password);
        }}
      >
        <h1>墨鱼</h1>
        <p className="subtitle">请输入访问密码</p>
        <input
          data-testid="login-password"
          type="password"
          value={password}
          placeholder="访问密码"
          autoFocus
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