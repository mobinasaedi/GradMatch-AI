import { useState } from "react";
import { api } from "../api";

function EmailBox({ professor, onChanged }) {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const lookup = async () => {
    setBusy(true);
    setError("");
    try {
      setResult(await api.emailLookup(professor.id, url));
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (email) => {
    try {
      await api.confirmEmail(professor.id, email, result.source_url);
      setResult(null);
      onChanged();
    } catch (e) {
      setError(e.message);
    }
  };

  if (professor.email) {
    return (
      <p>
        <strong>Email:</strong> <a href={`mailto:${professor.email}`}>{professor.email}</a>{" "}
        <a href={professor.email_source_url} target="_blank" rel="noreferrer">(source)</a>
      </p>
    );
  }

  return (
    <div className="emailbox">
      <p className="muted">No public email stored (we never guess one). Paste the professor's official page to look for it:</p>
      <div className="row">
        <input placeholder="https://www.cs.university.edu/~professor" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button onClick={lookup} disabled={busy || !url}>Look up</button>
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <div>
          <p className="muted">{result.note}</p>
          <ul>
            {result.candidates.map((c) => (
              <li key={c.email}>
                {c.email} {c.local_part_matches_name && <span className="badge">matches name</span>}{" "}
                <button onClick={() => confirm(c.email)}>Confirm & save</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Card({ item, onChanged, onTrack }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(null);
  const { professor: p, explanation: ex } = item;

  const showDraft = async () => {
    setDraft(await api.outreachDraft(item.outreach_id));
    await api.updateOutreach(item.outreach_id, { status: "draft_ready" });
    onChanged();
  };

  return (
    <article className="card result">
      <div className="head">
        <span className="rank">#{item.rank}</span>
        <div>
          <h3>{p.name}</h3>
          <p className="muted">
            {p.institution_name} ({p.country_code}) · {p.works_count} works ·{" "}
            <a href={p.openalex_url} target="_blank" rel="noreferrer">OpenAlex profile</a>
          </p>
        </div>
        <div className="score" title={`semantic ${item.semantic_score} / lexical ${item.lexical_score}`}>
          {item.score}
          <small>match</small>
        </div>
      </div>

      {p.topics.length > 0 && <p><strong>Research areas:</strong> {p.topics.join(", ")}</p>}
      <p><strong>Why this match:</strong> {ex.summary}</p>

      <button className="link" onClick={() => setOpen(!open)}>{open ? "Hide evidence" : "Show evidence"}</button>
      {open && (
        <div className="evidence">
          {ex.matched_topics.length > 0 && <p><strong>Shared topics:</strong> {ex.matched_topics.join(", ")}</p>}
          {ex.shared_terms.length > 0 && <p><strong>Overlapping terms:</strong> {ex.shared_terms.join(", ")}</p>}
          <strong>Most relevant recent papers</strong>
          <ul>
            {ex.evidence_papers.map((paper) => (
              <li key={paper.title}>
                {paper.doi ? <a href={paper.doi} target="_blank" rel="noreferrer">{paper.title}</a> : paper.title}
                {paper.year ? ` (${paper.year})` : ""} <span className="muted">similarity {paper.similarity}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <EmailBox professor={p} onChanged={onChanged} />

      <div className="row">
        <button onClick={showDraft}>Generate email draft</button>
        <button onClick={onTrack}>Open tracker</button>
      </div>
      {draft && (
        <div className="draft">
          <p className="muted">{draft.note}</p>
          <input readOnly value={draft.subject} />
          <textarea readOnly rows={12} value={draft.body} />
          <button onClick={() => navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`)}>Copy</button>
        </div>
      )}
    </article>
  );
}

export default function Results({ run, onChanged, onTrack }) {
  if (!run) return <section className="card"><p>No matches yet. Complete step 2 first.</p></section>;
  return (
    <div>
      {run.warnings.length > 0 && (
        <div className="banner warn">{run.warnings.map((w) => <div key={w}>{w}</div>)}</div>
      )}
      <p className="muted">
        Ranked with the <strong>{run.backend}</strong> backend. Candidates come from OpenAlex and may include non-faculty
        researchers: verify on the official page.
      </p>
      {run.results.map((item) => (
        <Card key={item.professor.id} item={item} onChanged={onChanged} onTrack={onTrack} />
      ))}
    </div>
  );
}
