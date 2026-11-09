import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import UploadStep from "./components/UploadStep.jsx";
import ProfileEditor from "./components/ProfileEditor.jsx";
import SearchStep from "./components/SearchStep.jsx";
import Results from "./components/Results.jsx";
import Tracker from "./components/Tracker.jsx";
import AuthScreen from "./components/AuthScreen.jsx";

const TABS = [
  { id: "profile", label: "1. Resume & profile" },
  { id: "search", label: "2. Countries & universities" },
  { id: "results", label: "3. Top matches" },
  { id: "tracker", label: "4. Email tracker" },
];
const STORAGE_KEY = "gradmatch.studentId";

export default function App() {
  const [tab, setTab] = useState("profile");
  const [user, setUser] = useState(undefined);
  const [student, setStudent] = useState(null);
  const [run, setRun] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
    api.authMe().then(async (current) => {
      setUser(current);
      const s = await api.myStudent();
      if (s) {
        setStudent(s);
        localStorage.setItem(STORAGE_KEY, s.id);
        await api.latestRecommendations(s.id).then(setRun).catch(() => {});
      }
    }).catch(() => setUser(null));
  }, []);

  const onUploaded = (s) => {
    localStorage.setItem(STORAGE_KEY, s.id);
    setStudent(s);
    setRun(null);
  };

  const reset = async () => {
    if (!student) return;
    if (!window.confirm("Delete your resume, profile, matches and tracking data?")) return;
    await api.deleteStudent(student.id);
    localStorage.removeItem(STORAGE_KEY);
    setStudent(null);
    setRun(null);
    setTab("profile");
  };

  const refreshRun = useCallback(() => {
    if (student) api.latestRecommendations(student.id).then(setRun).catch(() => {});
  }, [student]);

  if (user === undefined) return <main className="auth-wrap"><section className="card">Loading your secure workspace…</section></main>;
  if (!user) return <AuthScreen onAuthenticated={async (signedIn) => { setUser(signedIn); const s = await api.myStudent(); if (s) { setStudent(s); localStorage.setItem(STORAGE_KEY, s.id); await api.latestRecommendations(s.id).then(setRun).catch(() => {}); } }} />;

  return (
    <div className="app">
      <header>
        <h1>GradMatch AI</h1>
        <p className="subtitle">Find supervisors whose research matches your resume, then track your outreach.</p>
        <div className="account-bar"><span>{user.email}</span><button onClick={async () => { await api.logout(); localStorage.removeItem(STORAGE_KEY); setUser(null); setStudent(null); setRun(null); }}>Sign out</button></div>
        {health?.status === "unreachable" && (
          <div className="banner error">Backend is not reachable. Start it with <code>make backend</code>.</div>
        )}
        {health?.status === "ok" && !health.openalex_key_configured && (
          <div className="banner warn">
            No <code>OPENALEX_API_KEY</code> configured: searches will likely fail. Get a free key at openalex.org/settings/api.
          </div>
        )}
      </header>

      <nav>
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "tab active" : "tab"}
            disabled={t.id !== "profile" && !student}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {tab === "profile" && (
          <>
            <UploadStep onUploaded={onUploaded} />
            {student && (
              <ProfileEditor student={student} onSaved={setStudent} onNext={() => setTab("search")} onDelete={reset} />
            )}
          </>
        )}
        {tab === "search" && student && (
          <SearchStep
            student={student}
            onDone={(r) => {
              setRun(r);
              setTab("results");
            }}
          />
        )}
        {tab === "results" && <Results run={run} onChanged={refreshRun} onTrack={() => setTab("tracker")} />}
        {tab === "tracker" && student && <Tracker student={student} />}
      </main>

      <footer>
        Matches are research-similarity suggestions from OpenAlex data, not admission or funding predictions. Always verify
        a professor's affiliation and openings on the official university page.
      </footer>
    </div>
  );
}
