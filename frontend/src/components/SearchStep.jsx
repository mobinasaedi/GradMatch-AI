import { useEffect, useState } from "react";
import { api } from "../api";

const MAX_UNIVERSITIES = 5; // keep in sync with MAX_UNIVERSITIES_PER_RUN on the backend

export default function SearchStep({ student, onDone }) {
  const [countries, setCountries] = useState([]);
  const [universities, setUniversities] = useState([]);
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [selectedUnis, setSelectedUnis] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.countries().then(setCountries).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (selectedCountries.length === 0) {
      setUniversities([]);
      return;
    }
    api.universities(selectedCountries).then((list) => {
      setUniversities(list);
      setSelectedUnis((prev) => prev.filter((k) => list.some((u) => u.key === k)));
    });
  }, [selectedCountries]);

  const toggle = (list, setList, value) =>
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

  const effectiveCount = selectedUnis.length || universities.length;
  const tooMany = effectiveCount > MAX_UNIVERSITIES;

  const search = async () => {
    setBusy(true);
    setError("");
    try {
      onDone(await api.recommend(student.id, { countries: selectedCountries, university_keys: selectedUnis, top_k: 10 }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card">
      <h2>Where do you want to study?</h2>
      <p className="muted">
        Searching: <strong>{(student.interests || []).slice(0, 3).join(", ") || "no interests set"}</strong>
      </p>

      <h3>Countries</h3>
      <div className="chips">
        {countries.map((c) => (
          <label key={c.code} className={selectedCountries.includes(c.code) ? "chip on" : "chip"}>
            <input type="checkbox" checked={selectedCountries.includes(c.code)}
              onChange={() => toggle(selectedCountries, setSelectedCountries, c.code)} />
            {c.name}
          </label>
        ))}
      </div>

      {universities.length > 0 && (
        <>
          <h3>Universities <span className="muted">(optional; none selected = all listed)</span></h3>
          <div className="chips">
            {universities.map((u) => (
              <label key={u.key} className={selectedUnis.includes(u.key) ? "chip on" : "chip"}>
                <input type="checkbox" checked={selectedUnis.includes(u.key)}
                  onChange={() => toggle(selectedUnis, setSelectedUnis, u.key)} />
                {u.name}
              </label>
            ))}
          </div>
        </>
      )}

      {tooMany && (
        <p className="error">Please narrow the search to at most {MAX_UNIVERSITIES} universities (currently {effectiveCount}).</p>
      )}
      {error && <p className="error">{error}</p>}
      <button className="primary" onClick={search}
        disabled={busy || selectedCountries.length === 0 || tooMany || !(student.interests || []).length}>
        {busy ? "Searching OpenAlex… this can take a minute" : "Find top 10 professors"}
      </button>
    </section>
  );
}
