import { useEffect, useState } from "react";
import { api } from "../api";

const toList = (text) =>
  text
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);

export default function ProfileEditor({ student, onSaved, onNext, onDelete }) {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setForm({
      name: student.name || "",
      field: student.field || "",
      gpa: student.gpa || "",
      interests: (student.interests || []).join(", "),
      skills: (student.skills || []).join(", "),
      research_experience: student.research_experience || "",
    });
  }, [student]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async (andContinue) => {
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateStudent(student.id, {
        name: form.name,
        field: form.field,
        gpa: form.gpa,
        interests: toList(form.interests),
        skills: toList(form.skills),
        research_experience: form.research_experience,
      });
      onSaved(updated);
      if (andContinue) onNext();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="card">
      <h2>Review your extracted profile</h2>
      <p className="muted">
        The extractor is rule-based and can miss things. Matching uses mainly your research interests, so make sure they are right.
      </p>
      <div className="grid">
        <label>Name<input value={form.name || ""} onChange={set("name")} /></label>
        <label>Field<input value={form.field || ""} onChange={set("field")} /></label>
        <label>GPA<input value={form.gpa || ""} onChange={set("gpa")} /></label>
      </div>
      <label>Research interests (comma separated)
        <textarea rows={2} value={form.interests || ""} onChange={set("interests")} />
      </label>
      <label>Skills (comma separated)
        <textarea rows={2} value={form.skills || ""} onChange={set("skills")} />
      </label>
      <label>Research experience
        <textarea rows={5} value={form.research_experience || ""} onChange={set("research_experience")} />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button onClick={() => save(false)} disabled={saving}>Save</button>
        <button className="primary" onClick={() => save(true)} disabled={saving}>Save & continue</button>
        <button className="danger" onClick={onDelete}>Delete my data</button>
      </div>
    </section>
  );
}
