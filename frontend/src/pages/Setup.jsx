import { useState } from "react";
import { Badge, Button, Card, CopyButton, Icon, SectionHead, Spinner } from "../ui";

const ENV_SNIPPET = `# backend/.env
OPENALEX_API_KEY=your-free-key

# optional
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini`;

export default function Setup({ meta, health, notify, onSeed }) {
  const [busy, setBusy] = useState(false);
  const integrations = meta?.integrations || [];
  const configured = integrations.filter((item) => item.configured).length;

  const seed = async () => {
    setBusy(true);
    try {
      await onSeed();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack">
      <Card className="setup-hero">
        <div>
          <p className="eyebrow">Configuration</p>
          <h2>
            {configured} of {integrations.length} integrations connected
          </h2>
          <p className="hint">
            Everything works without a single key: the bundled dataset drives the matcher. Keys unlock live
            search, AI-written emails and password-reset mail.
          </p>
        </div>
        <div className="setup-hero-side">
          <Badge tone={health?.openalex_key_configured ? "emerald" : "amber"} icon="database">
            {health?.openalex_key_configured ? "OpenAlex live" : "Demo dataset"}
          </Badge>
          <Badge tone={health?.llm_configured ? "violet" : "neutral"} icon="sparkles">
            {health?.llm_configured ? "LLM connected" : "Template drafts"}
          </Badge>
        </div>
      </Card>

      <div className="integration-grid">
        {integrations.map((item) => (
          <Card key={item.key} className={`integration ${item.configured ? "integration-on" : ""}`}>
            <div className="integration-head">
              <span className="integration-icon">
                <Icon
                  name={item.key === "openalex" ? "globe" : item.key === "llm" ? "sparkles" : item.key === "smtp" ? "mail" : "layers"}
                  size={17}
                />
              </span>
              <div>
                <h3>{item.name}</h3>
                <div className="row">
                  <Badge tone={item.required ? "rose" : "neutral"}>{item.required ? "required for live data" : "optional"}</Badge>
                  <Badge tone={item.configured ? "emerald" : "amber"} icon={item.configured ? "check" : "alert"}>
                    {item.configured ? "configured" : "not set"}
                  </Badge>
                </div>
              </div>
            </div>
            <p className="hint">{item.purpose}</p>
            <div className="env-row">
              <code>{item.env_var}</code>
              <CopyButton text={item.env_var} label="Copy" />
            </div>
            <p className="tiny">{item.docs_hint}</p>
            <a className="btn btn-ghost btn-sm" href={item.signup_url} target="_blank" rel="noreferrer">
              <Icon name="external" size={14} /> Get it here
            </a>
          </Card>
        ))}
      </div>

      <div className="setup-columns">
        <Card>
          <SectionHead eyebrow="How to add a key" title="Three steps" />
          <ol className="steps">
            <li>
              <span className="step-num">1</span>
              <div>
                <strong>Create the key</strong>
                <p>Open the provider page from the card above and copy the key.</p>
              </div>
            </li>
            <li>
              <span className="step-num">2</span>
              <div>
                <strong>Paste it in backend/.env</strong>
                <p>Never commit that file: it is already git-ignored.</p>
              </div>
            </li>
            <li>
              <span className="step-num">3</span>
              <div>
                <strong>Restart the API</strong>
                <p>Stop uvicorn and start it again; the status here flips to “configured”.</p>
              </div>
            </li>
          </ol>
          <div className="code-block">
            <pre>{ENV_SNIPPET}</pre>
            <CopyButton text={ENV_SNIPPET} label="Copy block" />
          </div>
        </Card>

        <Card>
          <SectionHead
            eyebrow="Database"
            title={meta?.database_dialect ? `${meta.database_dialect} connected` : "Database"}
            action={<Badge tone="emerald" icon="check">online</Badge>}
          />
          <div className="code-block small">
            <code>{meta?.database_url || "sqlite:///./gradmatch.db"}</code>
          </div>
          <ul className="table-stats">
            {(meta?.tables || []).map((table) => (
              <li key={table.table}>
                <span>{table.table.replace(/_/g, " ")}</span>
                <strong>{table.rows}</strong>
              </li>
            ))}
          </ul>
          <div className="row-between">
            <p className="tiny">
              Dataset: {meta?.demo_seeded ? "loaded" : "not loaded"} · {meta?.demo_data_dir}
            </p>
            <Button variant="ghost" icon={busy ? undefined : "database"} onClick={seed} disabled={busy}>
              {busy ? <Spinner /> : null} {meta?.demo_seeded ? "Re-sync dataset" : "Load dataset"}
            </Button>
          </div>
          {meta?.dataset_coverage && Object.keys(meta.dataset_coverage).length > 0 && (
            <ul className="coverage">
              {Object.entries(meta.dataset_coverage).map(([key, value]) => (
                <li key={key}>
                  <span>{key}</span>
                  <span className="tiny">
                    {value.professors} professors · {value.publications} papers
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card className="soft">
        <SectionHead eyebrow="Good to know" title="What each key actually changes" />
        <ul className="facts">
          <li>
            <Icon name="globe" size={15} />
            <div>
              <strong>OpenAlex</strong> — without it, search only covers the seeded universities. With it, every
              university in <code>backend/app/data/universities.json</code> is searched live and results are
              cached for {`CACHE_TTL_DAYS`} days.
            </div>
          </li>
          <li>
            <Icon name="sparkles" size={15} />
            <div>
              <strong>LLM</strong> — rewrites the deterministic template into a shorter, more personal email
              using the same match evidence. Any OpenAI-compatible endpoint works, including a local Ollama.
            </div>
          </li>
          <li>
            <Icon name="mail" size={15} />
            <div>
              <strong>SMTP</strong> — only used for password reset links. Ethereal gives a free test inbox if you
              want to demo the reset flow.
            </div>
          </li>
        </ul>
      </Card>
    </div>
  );
}
