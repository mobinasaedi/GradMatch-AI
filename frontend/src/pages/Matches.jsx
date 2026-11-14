import { useState } from "react";
import { api, STATUS_LABELS, STATUS_ORDER } from "../api";
import { band, dateTime, initials } from "../lib/format";
import { Badge, Button, Card, CountryTag, EmptyState, Icon, Meter, Modal, Ring, SectionHead } from "../ui";

function EmailBox({ professor, onChanged, notify }) {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(false);

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
      notify(`Saved ${email} with its official source`, "success");
      setResult(null);
      onChanged();
    } catch (e) {
      setError(e.message);
    }
  };

  if (professor.email) {
    return (
      <div className="email-saved">
        <Icon name="check" size={15} />
        <a href={`mailto:${professor.email}`}>{professor.email}</a>
        <a className="tiny" href={professor.email_source_url} target="_blank" rel="noreferrer">
          source
        </a>
      </div>
    );
  }

  return (
    <div className="email-collapsed-wrap">
      {!expanded ? (
        <button className="email-collapsed" onClick={() => setExpanded(true)} type="button">
          <Icon name="mail" size={14} />
          <span>No public email stored — scan the official page to add one</span>
          <Icon name="chevronRight" size={14} />
        </button>
      ) : (
        <div className="email-box">
          <div className="email-box-head">
            <Icon name="mail" size={15} />
            <span>Paste the professor&apos;s official page. The app never guesses an address.</span>
          </div>
          <div className="row">
            <input
              value={url}
              placeholder="https://www.cs.toronto.edu/~professor"
              onChange={(event) => setUrl(event.target.value)}
            />
            <Button variant="ghost" onClick={lookup} loading={busy} disabled={!url}>
              Scan page
            </Button>
          </div>
          {error && <p className="form-error">{error}</p>}
          {result && (
            <div className="email-results">
              <p className="tiny">{result.note}</p>
              {result.candidates.length ? (
                <ul>
                  {result.candidates.map((candidate) => (
                    <li key={candidate.email}>
                      <span>{candidate.email}</span>
                      {candidate.local_part_matches_name && <Badge tone="emerald">matches name</Badge>}
                      <Button variant="ghost" className="btn-sm" onClick={() => confirm(candidate.email)}>
                        Confirm
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="tiny">No address found on that page.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DraftModal({ open, onClose, outreachId, llmAvailable, notify }) {
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("template");

  const load = async (kind) => {
    setBusy(true);
    setMode(kind);
    try {
      const data = kind === "ai" ? await api.outreachDraftAi(outreachId) : await api.outreachDraft(outreachId);
      setDraft(data);
      if (kind === "ai" && data.engine === "template") notify(data.note, "info");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  if (open && !draft && !busy) load("template");

  return (
    <Modal
      open={open}
      onClose={() => {
        setDraft(null);
        onClose();
      }}
      title="Outreach email"
      footer={
        draft ? (
          <div className="row-between full">
            <span className="tiny">
              <Icon name="info" size={13} /> {draft.note}
            </span>
            <Button
              variant="primary"
              icon="copy"
              onClick={() => {
                navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
                notify("Email copied to clipboard", "success");
              }}
            >
              Copy email
            </Button>
          </div>
        ) : null
      }
    >
      <div className="draft-tabs">
        <button className={mode === "template" ? "seg active" : "seg"} onClick={() => load("template")} disabled={busy}>
          <Icon name="file" size={14} /> Template
        </button>
        <button
          className={mode === "ai" ? "seg active" : "seg"}
          onClick={() => load("ai")}
          disabled={busy || !llmAvailable}
          title={llmAvailable ? "Rewrite with your configured LLM" : "Add LLM_API_KEY in Keys & data"}
        >
          <Icon name="sparkles" size={14} /> AI version
        </button>
      </div>

      {draft ? (
        <div className="draft-body">
          <label className="field">
            <span>Subject</span>
            <input readOnly value={draft.subject} />
          </label>
          <label className="field">
            <span>Body</span>
            <textarea readOnly rows={14} value={draft.body} />
          </label>
          <div className="row">
            <Badge tone={draft.engine === "llm" ? "violet" : "neutral"} icon={draft.engine === "llm" ? "sparkles" : "file"}>
              {draft.engine === "llm" ? "AI generated" : "Built-in template"}
            </Badge>
            <a className="link" href={`mailto:?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`}>
              Open in mail client
            </a>
          </div>
        </div>
      ) : (
        <p className="tiny">Preparing draft…</p>
      )}
    </Modal>
  );
}

function MatchCard({ item, student, onChanged, notify, llmAvailable }) {
  const [open, setOpen] = useState(false);
  const [draftOpen, setDraftOpen] = useState(false);
  const [status, setStatus] = useState(item.outreach_status || "not_started");
  const [saving, setSaving] = useState(false);
  const { professor } = item;
  const itemBand = band(item.fit);
  const topSimilarity = Math.max(0, ...item.explanation.evidence_papers.map((p) => p.similarity));

  const changeStatus = async (value) => {
    setSaving(true);
    try {
      await api.updateOutreach(item.outreach_id, { status: value });
      setStatus(value);
      await onChanged();
      notify(`Marked ${professor.name} as ${STATUS_LABELS[value].toLowerCase()}`, "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const exportVcf = () => {
    const body = [
      "BEGIN:VCARD",
      "VERSION:3.0",
      `FN:${professor.name}`,
      `ORG:${professor.institution_name}`,
      professor.email ? `EMAIL:${professor.email}` : "",
      professor.openalex_url ? `URL:${professor.openalex_url}` : "",
      "END:VCARD",
    ]
      .filter(Boolean)
      .join("\n");
    const blob = new Blob([body], { type: "text/vcard" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${professor.name.replace(/\s+/g, "-")}.vcf`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <article className="match-card">
      <div className="match-head">
        <span className="rank">#{item.rank}</span>
        <span className="avatar avatar-lg">{initials(professor.name)}</span>
        <div className="match-identity">
          <h3>{professor.name}</h3>
          <p className="tiny">
            <CountryTag code={professor.country_code} /> {professor.institution_name} ·{" "}
            {professor.works_count} papers indexed
            {professor.openalex_url && (
              <>
                {" · "}
                <a href={professor.openalex_url} target="_blank" rel="noreferrer">
                  OpenAlex <Icon name="external" size={11} />
                </a>
              </>
            )}
          </p>
        </div>
        <div className="match-score">
          <Ring value={item.fit} size={62} stroke={6} label={Math.round(item.fit)} />
          <span className={`fit-pill fit-${itemBand.key}`}>{itemBand.label}</span>
        </div>
      </div>

      {professor.topics?.length > 0 && (
        <div className="chip-wrap">
          {professor.topics.slice(0, 5).map((topic) => (
            <span key={topic} className="chip chip-muted">
              {topic}
            </span>
          ))}
        </div>
      )}

      <p className="why">
        <Icon name="sparkles" size={15} /> {item.explanation.summary}
      </p>

      <div className="match-metrics">
        <div>
          <span className="tiny">Semantic</span>
          <Meter value={item.fit_semantic} tone="violet" />
        </div>
        <div>
          <span className="tiny">Lexical (TF-IDF)</span>
          <Meter value={item.fit_lexical} tone="cyan" />
        </div>
      </div>

      <button className="disclosure" onClick={() => setOpen((value) => !value)}>
        <Icon name={open ? "chevronDown" : "chevronRight"} size={15} />
        {open ? "Hide evidence" : "Show evidence behind this score"}
      </button>

      {open && (
        <div className="evidence">
          {item.explanation.matched_topics?.length > 0 && (
            <div>
              <p className="eyebrow">Shared research topics</p>
              <div className="chip-wrap">
                {item.explanation.matched_topics.map((topic) => (
                  <span key={topic} className="chip chip-indigo">
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}
          {item.explanation.shared_terms?.length > 0 && (
            <div>
              <p className="eyebrow">Overlapping terms</p>
              <div className="chip-wrap">
                {item.explanation.shared_terms.map((term) => (
                  <span key={term} className="chip chip-muted">
                    {term}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div>
            <p className="eyebrow">Most relevant recent papers</p>
            <ul className="paper-list">
              {item.explanation.evidence_papers.map((paper) => (
                <li key={paper.title}>
                  <div className="paper-main">
                    {paper.doi ? (
                      <a href={paper.doi} target="_blank" rel="noreferrer">
                        {paper.title}
                      </a>
                    ) : (
                      <span>{paper.title}</span>
                    )}
                    <span className="tiny">{paper.year || "n.d."}</span>
                  </div>
                  <div className="paper-bar">
                    <span style={{ width: `${Math.max(6, (paper.similarity / Math.max(topSimilarity, 1)) * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <EmailBox professor={professor} onChanged={onChanged} notify={notify} />

      <div className="match-actions">
        <Button variant="primary" icon="mail" onClick={() => setDraftOpen(true)}>
          Draft email
        </Button>
        <div className="status-select">
          <select value={status} disabled={saving} onChange={(event) => changeStatus(event.target.value)}>
            {STATUS_ORDER.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </div>
        <Button variant="ghost" icon="download" onClick={exportVcf} className="btn-sm">
          vCard
        </Button>
      </div>

      <DraftModal
        open={draftOpen}
        onClose={() => setDraftOpen(false)}
        outreachId={item.outreach_id}
        llmAvailable={llmAvailable}
        notify={notify}
      />
    </article>
  );
}

export default function Matches({ run, student, meta, notify, onChanged, onNavigate }) {
  const [warningOpen, setWarningOpen] = useState(true);

  if (!run?.results?.length) {
    return (
      <Card>
        <EmptyState
          icon="compass"
          title="No shortlist yet"
          hint="Pick your destinations and run the matcher — with the bundled dataset it takes a couple of seconds."
          action={
            <Button variant="primary" icon="arrowRight" onClick={() => onNavigate("search")}>
              Go to search
            </Button>
          }
        />
      </Card>
    );
  }

  const llmAvailable = Boolean(meta?.integrations?.find((item) => item.key === "llm")?.configured);
  const demo = run.data_source === "demo-dataset";

  const exportCsv = () => {
    const header = ["rank", "name", "institution", "country", "fit", "score", "topics", "email"];
    const rows = run.results.map((item) => [
      item.rank,
      item.professor.name,
      item.professor.institution_name,
      item.professor.country_code,
      item.fit,
      item.score,
      (item.explanation.matched_topics || []).join("; "),
      item.professor.email || "",
    ]);
    const csv = [header, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `gradmatch-shortlist-${run.run_id}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    notify("Shortlist exported as CSV", "success");
  };

  return (
    <div className="stack">
      <Card className="run-summary">
        <div className="run-summary-main">
          <p className="eyebrow">Search run #{run.run_id}</p>
          <h2>
            {run.results.length} candidates · avg fit{" "}
            {Math.round(run.results.reduce((sum, item) => sum + item.fit, 0) / run.results.length)}
          </h2>
          <div className="meta-row">
            <Badge tone={demo ? "amber" : "emerald"} icon="database">
              {demo ? "Bundled demo dataset" : "OpenAlex live"}
            </Badge>
            <Badge tone="neutral" icon="layers">
              {run.backend} scorer
            </Badge>
            <Badge tone="neutral" icon="clock">
              {dateTime(run.created_at)}
            </Badge>
            {run.params?.university_names?.length ? (
              <Badge tone="neutral" icon="globe">
                {run.params.university_names.length} universities
              </Badge>
            ) : null}
          </div>
        </div>
        <div className="row">
          <Button variant="ghost" icon="printer" onClick={() => window.print()} className="btn-sm">
            Print / PDF
          </Button>
          <Button variant="ghost" icon="download" onClick={exportCsv} className="btn-sm">
            CSV
          </Button>
          <Button variant="ghost" icon="refresh" onClick={() => onNavigate("search")} className="btn-sm">
            New search
          </Button>
        </div>
      </Card>

      {run.warnings?.length > 0 && warningOpen && (
        <div className="banner banner-info">
          <Icon name="info" size={16} />
          <div className="banner-body">
            {run.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
          <button className="icon-btn" onClick={() => setWarningOpen(false)} aria-label="Dismiss">
            <Icon name="x" size={14} />
          </button>
        </div>
      )}

      <div className="print-only print-head">
        <h1>GradMatch AI — supervisor shortlist</h1>
        <p>
          {student?.name || "Applicant"} · {student?.field || ""} · generated {dateTime(run.created_at)}
        </p>
      </div>

      <div className="match-list">
        {run.results.map((item) => (
          <MatchCard
            key={item.professor.id}
            item={item}
            student={student}
            notify={notify}
            onChanged={onChanged}
            llmAvailable={llmAvailable}
          />
        ))}
      </div>

      <Card className="soft">
        <SectionHead
          eyebrow="Method"
          title="How the ranking is built"
          hint="score = α · semantic + (1 − α) · TF-IDF cosine, where semantic mixes the professor profile with the three most similar papers."
        />
        <div className="method-grid">
          <div>
            <h4>1 · Candidates</h4>
            <p className="tiny">Authors active on your topics at the selected institutions, filtered by affiliation and output.</p>
          </div>
          <div>
            <h4>2 · Scoring</h4>
            <p className="tiny">Text overlap on topics, abstracts and keywords; every number on screen comes from this step.</p>
          </div>
          <div>
            <h4>3 · Evidence</h4>
            <p className="tiny">Shared terms are the largest TF-IDF contributions; papers are the highest-similarity works.</p>
          </div>
          <div>
            <h4>4 · Fit (0–100)</h4>
            <p className="tiny">A monotone rescale of the raw cosine inside this pool — presentation only, the order never changes.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
