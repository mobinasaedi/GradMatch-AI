import { useEffect, useState } from "react";
import { api } from "../api";
import { Button, Icon } from "../ui";

const FEATURES = [
  {
    icon: "file",
    title: "Resume → research profile",
    text: "A PDF or DOCX is parsed locally; the extracted interests and skills stay editable before any matching happens.",
  },
  {
    icon: "sparkles",
    title: "Explainable supervisor matching",
    text: "Hybrid TF-IDF and semantic scoring over recent OpenAlex papers, with the shared terms and evidence papers behind every rank.",
  },
  {
    icon: "mail",
    title: "Outreach that stays honest",
    text: "Draft the email, track every status change, and never guess an address: an email is stored only from the official page.",
  },
];

export default function Landing({ onAuthenticated }) {
  const params = new URLSearchParams(window.location.search);
  const initialToken = params.get("reset_token") || "";
  const [mode, setMode] = useState(initialToken ? "reset" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(initialToken);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (mode === "login" || mode === "register") {
        const user =
          mode === "login" ? await api.login(email, password) : await api.register(email, password);
        onAuthenticated(user);
      } else if (mode === "forgot") {
        const result = await api.forgotPassword(email);
        setMessage(result.message);
      } else {
        const result = await api.resetPassword(token, password);
        setMessage(result.message);
        setMode("login");
        setPassword("");
        window.history.replaceState({}, "", window.location.pathname);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const titles = {
    login: "Welcome back",
    register: "Create your workspace",
    forgot: "Reset your password",
    reset: "Choose a new password",
  };

  return (
    <div className="landing">
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />
      <div className="landing-grid" />

      <section className="landing-copy">
        <div className="brand brand-lg">
          <span className="brand-mark">
            <Icon name="sparkles" size={18} />
          </span>
          <span>
            GradMatch <em>AI</em>
          </span>
        </div>

        <h1>
          Find the supervisor
          <br />
          whose work <span className="grad-text nowrap">matches yours</span>.
        </h1>
        <p className="landing-lede">
          Upload your academic resume and get a ranked, explainable shortlist of researchers whose recent
          publications overlap with your interests — then track every email until you get a reply.
        </p>

        <div className="landing-stats">
          <div>
            <strong>{health?.professors_indexed ?? "—"}</strong>
            <span>professors indexed</span>
          </div>
          <div>
            <strong>{health?.publications_indexed ?? "—"}</strong>
            <span>recent papers</span>
          </div>
          <div>
            <strong>24</strong>
            <span>universities</span>
          </div>
          <div>
            <strong>6</strong>
            <span>countries</span>
          </div>
        </div>

        <ul className="feature-list">
          {FEATURES.map((feature) => (
            <li key={feature.title}>
              <span className="feature-icon">
                <Icon name={feature.icon} size={17} />
              </span>
              <div>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </div>
            </li>
          ))}
        </ul>

        <div className="landing-status">
          <span className={`dot ${health?.status === "ok" ? "dot-live" : "dot-off"}`} />
          {health?.status === "ok" ? (
            <span>
              API online · {health.professors_indexed} professors indexed ·{" "}
              {health.openalex_key_configured ? "live OpenAlex search" : "bundled dataset (no key needed)"}
            </span>
          ) : (
            <span>API unreachable — start the backend on port 8000.</span>
          )}
        </div>
      </section>

      <section className="auth-card">
        <header>
          <p className="eyebrow">Master&apos;s application workspace</p>
          <h2>{titles[mode]}</h2>
          <p className="hint">
            {mode === "login" && "Sign in to continue your shortlist and outreach tracker."}
            {mode === "register" && "One account keeps your profile, matches and emails together."}
            {mode === "forgot" && "We will send a one-time reset link if the address exists."}
            {mode === "reset" && "Pick something long and unique to this account."}
          </p>
        </header>

        <form onSubmit={submit}>
          {(mode === "login" || mode === "register" || mode === "forgot") && (
            <label className="field">
              <span>Email address</span>
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                placeholder="you@university.edu"
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          )}

          {mode === "reset" && (
            <label className="field">
              <span>Reset token</span>
              <input required value={token} onChange={(e) => setToken(e.target.value)} />
            </label>
          )}

          {(mode === "login" || mode === "register" || mode === "reset") && (
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                required
                minLength={mode === "login" ? 1 : 12}
                maxLength={128}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                placeholder={mode === "login" ? "Your password" : "At least 12 characters"}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
          )}

          {error && (
            <p className="form-error">
              <Icon name="alert" size={15} /> {error}
            </p>
          )}
          {message && (
            <p className="form-success">
              <Icon name="check" size={15} /> {message}
            </p>
          )}

          <Button variant="primary" type="submit" loading={busy} className="btn-block">
            {{
              login: "Sign in",
              register: "Create account",
              forgot: "Send reset link",
              reset: "Update password",
            }[mode]}
          </Button>
        </form>

        <div className="auth-links">
          {mode !== "login" && (
            <button type="button" className="link" onClick={() => { setMode("login"); setError(""); setMessage(""); }}>
              Back to sign in
            </button>
          )}
          {mode === "login" && (
            <>
              <button type="button" className="link" onClick={() => setMode("register")}>
                Create an account
              </button>
              <button type="button" className="link" onClick={() => setMode("forgot")}>
                Forgot password?
              </button>
            </>
          )}
          {mode === "register" && (
            <button type="button" className="link" onClick={() => setMode("login")}>
              Already have an account? Sign in
            </button>
          )}
        </div>

        <p className="auth-note">
          <Icon name="shield" size={14} /> Argon2id hashing · HttpOnly session cookies · your resume stays in
          your own database.
        </p>
      </section>
    </div>
  );
}
