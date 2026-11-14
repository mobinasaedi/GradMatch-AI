import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import Landing from "./components/Landing";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Search from "./pages/Search";
import Matches from "./pages/Matches";
import Outreach from "./pages/Outreach";
import Setup from "./pages/Setup";
import { Icon, Toasts } from "./ui";

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "grid", title: "Your application, at a glance", hint: "Fit scores, progress and the state of your outreach." },
  { id: "profile", label: "Resume & profile", icon: "file", title: "Resume and research profile", hint: "Upload once, then refine what the extractor found." },
  { id: "search", label: "Find supervisors", icon: "compass", title: "Where do you want to study?", hint: "Pick countries and universities, then run the matcher." },
  { id: "matches", label: "Shortlist", icon: "sparkles", title: "Your supervisor shortlist", hint: "Ranked by how closely recent publications overlap with your profile." },
  { id: "outreach", label: "Outreach", icon: "mail", title: "Email tracker", hint: "Every professor, every status change, in one timeline." },
  { id: "setup", label: "Keys & data", icon: "key", title: "API keys, database and dataset", hint: "What is configured, what is missing, and how to add it." },
];

const STORAGE_KEY = "gradmatch.studentId";

let toastCounter = 0;

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [user, setUser] = useState(undefined);
  const [student, setStudent] = useState(null);
  const [run, setRun] = useState(null);
  const [health, setHealth] = useState(null);
  const [meta, setMeta] = useState(null);
  const [overview, setOverview] = useState(null);
  const [runs, setRuns] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [navOpen, setNavOpen] = useState(false);

  const notify = useCallback((message, tone = "info") => {
    const id = ++toastCounter;
    setToasts((list) => [...list, { id, message, tone }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 5200);
  }, []);

  const loadStudentData = useCallback(async (current) => {
    if (!current) {
      setStudent(null);
      setRun(null);
      setOverview(null);
      setRuns([]);
      return;
    }
    setStudent(current);
    localStorage.setItem(STORAGE_KEY, current.id);
    const [latestRun, overviewData, runHistory] = await Promise.all([
      api.latestRecommendations(current.id).catch(() => null),
      api.overview(current.id).catch(() => null),
      api.runs(current.id).catch(() => []),
    ]);
    setRun(latestRun);
    setOverview(overviewData);
    setRuns(runHistory || []);
  }, []);

  const refresh = useCallback(async () => {
    const current = await api.myStudent().catch(() => null);
    await loadStudentData(current);
  }, [loadStudentData]);

  const refreshMeta = useCallback(async () => {
    const [stats, healthData] = await Promise.all([
      api.metaStats().catch(() => null),
      api.health().catch(() => ({ status: "unreachable" })),
    ]);
    setMeta(stats);
    setHealth(healthData);
  }, []);

  useEffect(() => {
    (async () => {
      await refreshMeta();
      try {
        const current = await api.authMe();
        setUser(current);
        const currentStudent = await api.myStudent();
        await loadStudentData(currentStudent);
      } catch {
        setUser(null);
      }
    })();
  }, [loadStudentData, refreshMeta]);

  const signOut = async () => {
    await api.logout().catch(() => {});
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
    setStudent(null);
    setRun(null);
    setOverview(null);
    setTab("dashboard");
  };

  const onAuthenticated = async (signedIn) => {
    setUser(signedIn);
    const currentStudent = await api.myStudent().catch(() => null);
    await loadStudentData(currentStudent);
    await refreshMeta();
  };

  const current = useMemo(() => NAV.find((item) => item.id === tab) || NAV[0], [tab]);

  const navigate = (next) => {
    setTab(next);
    setNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (user === undefined) {
    return (
      <div className="boot">
        <span className="brand-mark brand-mark-lg">
          <Icon name="sparkles" size={22} />
        </span>
        <p>Loading your workspace…</p>
      </div>
    );
  }

  if (!user) return <Landing onAuthenticated={onAuthenticated} />;

  return (
    <div className="shell">
      <div className="shell-glow" />
      <aside className={`sidebar ${navOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">
            <Icon name="sparkles" size={18} />
          </span>
          <span>
            GradMatch <em>AI</em>
          </span>
        </div>

        <nav className="nav">
          {NAV.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${tab === item.id ? "active" : ""}`}
              onClick={() => navigate(item.id)}
            >
              <Icon name={item.icon} size={17} />
              <span>{item.label}</span>
              {item.id === "matches" && run?.results?.length ? (
                <span className="nav-count">{run.results.length}</span>
              ) : null}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="dataset-card">
            <div className="dataset-head">
              <Icon name="database" size={15} />
              <span>{meta?.database_dialect || "sqlite"}</span>
            </div>
            <p>
              <strong>{meta?.counts?.professors ?? "—"}</strong> professors ·{" "}
              <strong>{meta?.counts?.publications ?? "—"}</strong> papers
            </p>
            <p className="tiny">
              {health?.openalex_key_configured ? "Live OpenAlex search" : "Bundled dataset · no key required"}
            </p>
          </div>
          <div className="user-row">
            <span className="avatar avatar-sm">{(user.email || "?").slice(0, 1).toUpperCase()}</span>
            <span className="user-email" title={user.email}>
              {user.email}
            </span>
            <button className="icon-btn" onClick={signOut} aria-label="Sign out" title="Sign out">
              <Icon name="logout" size={16} />
            </button>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="icon-btn nav-toggle" onClick={() => setNavOpen((v) => !v)} aria-label="Menu">
            <Icon name={navOpen ? "x" : "filter"} size={18} />
          </button>
          <div className="topbar-title">
            <h1>{current.title}</h1>
            <p>{current.hint}</p>
          </div>
          <div className="topbar-tags">
            {run ? (
              <span className={`pill ${run.data_source === "demo-dataset" ? "pill-amber" : "pill-emerald"}`}>
                <span className="dot" />
                {run.data_source === "demo-dataset" ? "Demo dataset" : "Live OpenAlex"}
              </span>
            ) : null}
            <span className="pill pill-muted">
              <Icon name="layers" size={13} /> v{health?.version || "0.2.0"}
            </span>
          </div>
        </header>

        {health?.status === "unreachable" && (
          <div className="banner banner-error">
            <Icon name="alert" size={16} /> The API is not reachable. Start the backend with{" "}
            <code>uvicorn app.main:app --port 8000</code>.
          </div>
        )}

        <main className="content">
          {tab === "dashboard" && (
            <Dashboard
              student={student}
              run={run}
              overview={overview}
              runs={runs}
              meta={meta}
              onNavigate={navigate}
              onOpenRun={async (runId) => {
                const data = await api.getRun(student.id, runId);
                setRun(data);
                navigate("matches");
              }}
            />
          )}
          {tab === "profile" && (
            <Profile
              student={student}
              onChanged={async (updated) => {
                if (updated) {
                  await loadStudentData(updated);
                } else {
                  await refresh();
                }
                await refreshMeta();
              }}
              notify={notify}
              onNavigate={navigate}
            />
          )}
          {tab === "search" && (
            <Search
              student={student}
              meta={meta}
              history={runs}
              notify={notify}
              onNavigate={navigate}
              onDone={async (newRun) => {
                setRun(newRun);
                await refresh();
                navigate("matches");
              }}
            />
          )}
          {tab === "matches" && (
            <Matches
              run={run}
              student={student}
              meta={meta}
              notify={notify}
              onChanged={refresh}
              onNavigate={navigate}
            />
          )}
          {tab === "outreach" && (
            <Outreach student={student} notify={notify} onNavigate={navigate} />
          )}
          {tab === "setup" && (
            <Setup
              meta={meta}
              health={health}
              notify={notify}
              onSeed={async () => {
                const report = await api.seedDemo();
                await refreshMeta();
                notify(
                  report.professors_inserted
                    ? `Imported ${report.professors_inserted} professors and ${report.publications_inserted} publications.`
                    : "Dataset already loaded — nothing new to import.",
                  "success",
                );
              }}
            />
          )}
        </main>

        <footer className="app-footer">
          Matches are research-similarity suggestions from academic metadata, not predictions of admission or
          funding. Always verify affiliation and openings on the official university page.
        </footer>
      </div>

      <Toasts items={toasts} onDismiss={(id) => setToasts((list) => list.filter((t) => t.id !== id))} />
    </div>
  );
}
