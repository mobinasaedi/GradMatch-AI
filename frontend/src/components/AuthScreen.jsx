import { useState } from "react";
import { api } from "../api";

export default function AuthScreen({ onAuthenticated }) {
  const params = new URLSearchParams(window.location.search);
  const initialToken = params.get("reset_token") || "";
  const [mode, setMode] = useState(initialToken ? "reset" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(initialToken);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      if (mode === "login" || mode === "register") {
        const user = mode === "login" ? await api.login(email, password) : await api.register(email, password);
        onAuthenticated(user);
      } else if (mode === "forgot") {
        const result = await api.forgotPassword(email); setMessage(result.message);
      } else {
        const result = await api.resetPassword(token, password); setMessage(result.message); setMode("login"); setPassword("");
        window.history.replaceState({}, "", window.location.pathname);
      }
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const title = { login: "Welcome back", register: "Create your account", forgot: "Reset your password", reset: "Choose a new password" }[mode];
  return <main className="auth-wrap"><section className="card auth-card">
    <h1>GradMatch AI</h1><h2>{title}</h2>
    <p className="muted">Your academic supervisor discovery workspace.</p>
    <form onSubmit={submit}>
      {(mode === "login" || mode === "register" || mode === "forgot") && <label>Email address<input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} /></label>}
      {mode === "reset" && <label>Reset token<input required value={token} onChange={e => setToken(e.target.value)} /></label>}
      {(mode === "login" || mode === "register" || mode === "reset") && <label>Password<input type="password" required minLength={mode === "login" ? 1 : 12} maxLength={128} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={e => setPassword(e.target.value)} /><small className="muted">{mode === "login" ? "" : "Use at least 12 characters."}</small></label>}
      {error && <p className="error">{error}</p>}{message && <p className="success">{message}</p>}
      <button className="primary" type="submit" disabled={busy}>{busy ? "Please wait…" : ({ login: "Sign in", register: "Create account", forgot: "Send reset link", reset: "Update password" }[mode])}</button>
    </form>
    <div className="auth-links">
      {mode !== "login" && <button className="link" onClick={() => {setMode("login");setError("");setMessage("");}}>Back to sign in</button>}
      {mode === "login" && <><button className="link" onClick={() => setMode("register")}>Create an account</button><button className="link" onClick={() => setMode("forgot")}>Forgot password?</button></>}
      {mode === "register" && <button className="link" onClick={() => setMode("login")}>Already have an account? Sign in</button>}
    </div>
  </section></main>;
}
