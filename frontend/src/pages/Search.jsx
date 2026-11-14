import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { dateTime } from "../lib/format";
import { Badge, Button, Card, CountryTag, EmptyState, Icon, SectionHead, Spinner } from "../ui";

const MAX_UNIVERSITIES = 5;

const LOADING_STEPS = [
  "Reading your research interests…",
  "Collecting candidate researchers…",
  "Scoring recent publications…",
  "Building the explanations…",
];

export default function Search({ student, meta, history, onDone, onNavigate, notify }) {
  const [countries, setCountries] = useState([]);
  const [universities, setUniversities] = useState([]);
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [selectedUnis, setSelectedUnis] = useState([]);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const hasKey = Boolean(meta?.integrations?.find((item) => item.key === "openalex")?.configured);

  useEffect(() => {
    api.countries().then(setCountries).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedCountries.length) {
      setUniversities([]);
      setSelectedUnis([]);
      return;
    }
    api
      .universities(selectedCountries)
      .then((list) => {
        setUniversities(list);
        setSelectedUnis((prev) => {
          const kept = prev.filter((key) => list.some((uni) => uni.key === key));
          if (kept.length) return kept;
          if (list.length <= MAX_UNIVERSITIES) return []; // empty means “all in these countries”
          // Too many to run: preselect the ones that already have professors in the dataset,
          // so a demo never starts on a disabled button.
          const coverage = meta?.dataset_coverage || {};
          const withData = list.filter((uni) => (coverage[uni.key]?.professors || 0) > 0);
          if (!hasKey && withData.length) {
            return withData.slice(0, MAX_UNIVERSITIES).map((uni) => uni.key);
          }
          return [...list]
            .sort((a, b) => (coverage[b.key]?.professors || 0) - (coverage[a.key]?.professors || 0))
            .slice(0, MAX_UNIVERSITIES)
            .map((uni) => uni.key);
        });
      })
      .catch((e) => setError(e.message));
  }, [selectedCountries, meta, hasKey]);

  useEffect(() => {
    if (!busy) return undefined;
    setStep(0);
    const timer = setInterval(() => setStep((value) => Math.min(LOADING_STEPS.length - 1, value + 1)), 1400);
    return () => clearInterval(timer);
  }, [busy]);

  const coverage = meta?.dataset_coverage || {};
  const universityCounts = useMemo(() => {
    const counts = {};
    for (const country of selectedCountries) {
      counts[country] = universities.filter((uni) => uni.country_code === country).length;
    }
    return counts;
  }, [selectedCountries, universities]);

  const toggleCountry = (code) => {
    setSelectedCountries((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };

  const toggleUni = (key) => {
    setSelectedUnis((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  };

  const effectiveCount = selectedUnis.length || universities.length;
  const tooMany = effectiveCount > MAX_UNIVERSITIES;
  const interests = student?.interests || [];
  const ready = Boolean(student) && interests.length > 0 && selectedCountries.length > 0 && !tooMany;

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await api.recommend(student.id, {
        countries: selectedCountries,
        university_keys: selectedUnis,
        top_k: 10,
      });
      const demo = result.data_source === "demo-dataset";
      notify(
        demo
          ? `Shortlist ready from the bundled dataset (${result.results.length} candidates)`
          : `Shortlist ready (${result.results.length} candidates from OpenAlex)`,
        "success",
      );
      onDone(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!student) {
    return (
      <Card>
        <EmptyState
          icon="file"
          title="Upload a resume first"
          hint="The matcher needs your research interests before it can rank anyone."
          action={
            <Button variant="primary" onClick={() => onNavigate("profile")}>
              Go to resume
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <div className="search-layout">
      <div className="stack">
        <Card>
          <SectionHead
            eyebrow="Step 2"
            title="Countries"
            hint="Every country adds universities to the candidate pool. Five universities per search keeps API usage predictable."
          />
          <div className="country-grid">
            {countries.map((country) => {
              const active = selectedCountries.includes(country.code);
              return (
                <button
                  key={country.code}
                  className={`country-card ${active ? "country-card-on" : ""}`}
                  onClick={() => toggleCountry(country.code)}
                  type="button"
                >
                  <span className="country-top">
                    <CountryTag code={country.code} />
                    <span className={`country-toggle ${active ? "on" : ""}`}>
                      {active ? <Icon name="check" size={11} /> : <Icon name="plus" size={11} />}
                    </span>
                  </span>
                  <span className="country-name">{country.name}</span>
                  <span className="tiny">{active ? "selected" : "tap to add"}</span>
                </button>
              );
            })}
          </div>
        </Card>

        {universities.length > 0 && (
          <Card>
            <SectionHead
              eyebrow="Step 2b"
              title="Universities"
              hint={`Leave all unchecked to use every university in the chosen countries. Above ${MAX_UNIVERSITIES}, the ones with local data are preselected.`}
              action={
                <div className="row">
                  <button
                    className="seg"
                    onClick={() => {
                      const coverage = meta?.dataset_coverage || {};
                      setSelectedUnis(
                        [...universities]
                          .sort((a, b) => (coverage[b.key]?.professors || 0) - (coverage[a.key]?.professors || 0))
                          .slice(0, MAX_UNIVERSITIES)
                          .map((uni) => uni.key),
                      );
                    }}
                  >
                    Pick top {MAX_UNIVERSITIES}
                  </button>
                  <button className="seg" onClick={() => setSelectedUnis([])}>
                    Use all in country
                  </button>
                  <span className={`pill ${tooMany ? "pill-rose" : "pill-muted"}`}>
                    {effectiveCount}/{MAX_UNIVERSITIES}
                  </span>
                </div>
              }
            />
            <ul className="uni-list">
              {universities.map((uni) => {
                const active = selectedUnis.includes(uni.key);
                const local = coverage[uni.key]?.professors || 0;
                return (
                  <li key={uni.key}>
                    <button className={`uni-row ${active ? "uni-row-on" : ""}`} onClick={() => toggleUni(uni.key)} type="button">
                      <span className={`checkbox ${active ? "checkbox-on" : ""}`}>
                        {active && <Icon name="check" size={12} />}
                      </span>
                      <span className="uni-main">
                        <strong>{uni.name}</strong>
                        <span className="tiny">
                          {uni.country} ·{" "}
                          <a href={uni.website} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                            {uni.website.replace("https://", "")}
                          </a>
                        </span>
                      </span>
                      {local > 0 ? (
                        <Badge tone="emerald">{local} indexed</Badge>
                      ) : (
                        <Badge tone="amber">needs API key</Badge>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
            {tooMany && (
              <p className="form-error">
                <Icon name="alert" size={15} /> Narrow it down to {MAX_UNIVERSITIES} universities (currently{" "}
                {effectiveCount}).
              </p>
            )}
          </Card>
        )}

        <Card className="run-card">
          <div className="run-copy">
            <p className="eyebrow">Step 3</p>
            <h2>Run the matcher</h2>
            <p className="hint">
              Searching for{" "}
              <strong>{interests.slice(0, 4).join(", ") || "no interests set"}</strong>
              {interests.length > 4 ? ` +${interests.length - 4} more` : ""}
            </p>
            {!interests.length && (
              <p className="form-error">
                <Icon name="alert" size={15} /> Add research interests on the profile page first.
              </p>
            )}
            {error && (
              <p className="form-error">
                <Icon name="alert" size={15} /> {error}
              </p>
            )}
          </div>
          <div className="run-action">
            <Button variant="primary" icon="zap" onClick={run} disabled={!ready || busy} loading={busy}>
              {busy ? "Matching…" : "Find top 10 supervisors"}
            </Button>
            <span className="tiny">
              {busy ? LOADING_STEPS[step] : `${effectiveCount} universities · hybrid scorer`}
            </span>
          </div>
        </Card>
      </div>

      <aside className="stack search-aside">
        <Card className="soft">
          <SectionHead eyebrow="Tip" title="Better topics, better matches" />
          <p className="hint">
            Interests that mirror paper titles work best: “retrieval-augmented generation” beats “AI”. The
            extractor already maps 18 canonical topics.
          </p>
          <div className="chip-wrap">
            {interests.slice(0, 8).map((interest) => (
              <span key={interest} className="chip chip-default">
                {interest}
              </span>
            ))}
          </div>
        </Card>

        <Card className="soft">
          <SectionHead eyebrow="History" title="Previous searches" />
          {history?.length ? (
            <ul className="run-list">
              {history.slice(0, 5).map((entry) => (
                <li key={entry.run_id}>
                  <div className="run-row static">
                    <span className="run-main">
                      <strong>{entry.university_names?.join(", ") || "Search"}</strong>
                      <span className="tiny">
                        {dateTime(entry.created_at)} · {entry.results_count} results
                      </span>
                    </span>
                    <Badge tone={entry.data_source === "demo-dataset" ? "amber" : "emerald"}>
                      {entry.data_source === "demo-dataset" ? "demo" : "live"}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="chart-empty">No searches yet.</p>
          )}
        </Card>

        {!meta?.demo_seeded && (
          <Card className="soft">
            <SectionHead eyebrow="Dataset" title="No local data" />
            <p className="hint">
              Load the bundled Toronto / Amsterdam / TU Munich dataset from the “Keys & data” page, or add an
              OpenAlex key for live search.
            </p>
            <Button variant="ghost" icon="database" onClick={() => onNavigate("setup")}>
              Open setup
            </Button>
          </Card>
        )}
      </aside>
    </div>
  );
}
