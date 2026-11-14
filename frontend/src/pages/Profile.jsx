import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { shortDate } from "../lib/format";
import { Badge, Button, Card, Icon, Meter, Modal, SectionHead, Spinner } from "../ui";

function TagInput({ label, values, onChange, placeholder }) {
  const [draft, setDraft] = useState("");

  const add = () => {
    const parts = draft
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .filter((part) => !values.some((value) => value.toLowerCase() === part.toLowerCase()));
    if (parts.length) onChange([...values, ...parts]);
    setDraft("");
  };

  return (
    <div className="field">
      <span>{label}</span>
      <div className="tag-input">
        {values.map((value) => (
          <span key={value} className="tag">
            {value}
            <button type="button" onClick={() => onChange(values.filter((item) => item !== value))} aria-label={`Remove ${value}`}>
              <Icon name="x" size={12} />
            </button>
          </span>
        ))}
        <input
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault();
              add();
            }
            if (event.key === "Backspace" && !draft && values.length) {
              onChange(values.slice(0, -1));
            }
          }}
          onBlur={add}
        />
      </div>
    </div>
  );
}

function Dropzone({ busy, onFile }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const pick = (file) => {
    if (file) onFile(file);
  };

  return (
    <div
      className={`dropzone ${dragging ? "dropzone-active" : ""} ${busy ? "dropzone-busy" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        pick(event.dataTransfer.files?.[0]);
      }}
      onClick={() => !busy && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        hidden
        onChange={(event) => {
          pick(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <span className="dropzone-icon">{busy ? <Spinner size={22} /> : <Icon name="file" size={24} />}</span>
      <h3>{busy ? "Reading your resume…" : "Drop your resume here"}</h3>
      <p>PDF or DOCX, up to 5 MB. Text is extracted on the server with PyMuPDF / python-docx.</p>
      <span className="dropzone-cta">{busy ? "Extracting profile" : "Browse files"}</span>
    </div>
  );
}

export default function Profile({ student, onChanged, notify, onNavigate }) {
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (!student) {
      setForm(null);
      return;
    }
    setForm({
      name: student.name || "",
      field: student.field || "",
      gpa: student.gpa || "",
      education: student.education || "",
      interests: student.interests || [],
      skills: student.skills || [],
      research_experience: student.research_experience || "",
    });
  }, [student]);

  const completeness = useMemo(() => {
    if (!form) return 0;
    const checks = [
      Boolean(form.name),
      Boolean(form.field),
      Boolean(form.gpa),
      form.interests.length > 0,
      form.skills.length > 0,
      Boolean(form.research_experience.trim()),
    ];
    return Math.round((checks.filter(Boolean).length / checks.length) * 100);
  }, [form]);

  const upload = async (file) => {
    setBusy(true);
    setError("");
    try {
      const created = await api.uploadResume(file);
      notify(`Profile extracted from ${created.filename}`, "success");
      await onChanged(created);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const save = async (andContinue) => {
    if (!student) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateStudent(student.id, {
        name: form.name,
        field: form.field,
        gpa: form.gpa,
        education: form.education,
        interests: form.interests,
        skills: form.skills,
        research_experience: form.research_experience,
      });
      notify("Profile saved", "success");
      await onChanged(updated);
      if (andContinue) onNavigate("search");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    await api.deleteStudent(student.id);
    setConfirmDelete(false);
    notify("Resume and all derived data deleted", "success");
    await onChanged(null);
  };

  if (!student) {
    return (
      <div className="stack">
        <Card>
          <SectionHead
            eyebrow="Step 1"
            title="Upload your academic resume"
            hint="The extractor is rule-based: it looks for education, research interests, skills and experience, then you correct it."
          />
          <Dropzone busy={busy} onFile={upload} />
          {error && <p className="form-error"><Icon name="alert" size={15} /> {error}</p>}
          <div className="hint-row">
            <Badge tone="neutral" icon="shield">Local parsing, no paid API</Badge>
            <Badge tone="neutral" icon="file">PDF · DOCX</Badge>
            <Badge tone="neutral" icon="database">Stored in your SQLite database</Badge>
          </div>
        </Card>
        <Card className="soft">
          <SectionHead eyebrow="What happens next" title="Three steps to a shortlist" />
          <ol className="steps">
            <li>
              <span className="step-num">1</span>
              <div>
                <strong>Extract & refine</strong>
                <p>Interests and skills are pulled out; you edit them into accurate research topics.</p>
              </div>
            </li>
            <li>
              <span className="step-num">2</span>
              <div>
                <strong>Choose destinations</strong>
                <p>Pick countries and universities; the search is capped to protect API credits.</p>
              </div>
            </li>
            <li>
              <span className="step-num">3</span>
              <div>
                <strong>Read the evidence</strong>
                <p>Each candidate comes with shared terms and the exact papers behind the score.</p>
              </div>
            </li>
          </ol>
        </Card>
      </div>
    );
  }

  if (!form) return null;

  return (
    <div className="stack">
      <Card>
        <SectionHead
          eyebrow="Step 1"
          title="Research profile"
          hint="Matching uses mostly your research interests, so make sure they read like the topics in papers."
          action={
            <div className="profile-score">
              <Meter value={completeness} />
              <span className="tiny">{completeness}% complete</span>
            </div>
          }
        />

        <div className="grid-3">
          <label className="field">
            <span>Full name</span>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="field">
            <span>Field</span>
            <input
              value={form.field}
              placeholder="Computer Engineering"
              onChange={(e) => setForm({ ...form, field: e.target.value })}
            />
          </label>
          <label className="field">
            <span>GPA</span>
            <input value={form.gpa} placeholder="18.2/20" onChange={(e) => setForm({ ...form, gpa: e.target.value })} />
          </label>
        </div>

        <TagInput
          label="Research interests"
          values={form.interests}
          onChange={(interests) => setForm({ ...form, interests })}
          placeholder="Add an interest and press Enter"
        />
        <TagInput
          label="Skills"
          values={form.skills}
          onChange={(skills) => setForm({ ...form, skills })}
          placeholder="Add a skill and press Enter"
        />

        <label className="field">
          <span>Research experience</span>
          <textarea
            rows={5}
            value={form.research_experience}
            placeholder="Thesis, projects, publications, lab work…"
            onChange={(e) => setForm({ ...form, research_experience: e.target.value })}
          />
        </label>

        {error && <p className="form-error"><Icon name="alert" size={15} /> {error}</p>}

        <div className="row-between">
          <div className="muted tiny">
            <Icon name="file" size={13} /> {student.filename} · uploaded {shortDate(student.created_at)}
          </div>
          <div className="row">
            <Button variant="ghost" onClick={() => setConfirmDelete(true)} icon="trash">
              Delete my data
            </Button>
            <Button variant="ghost" onClick={() => save(false)} loading={saving}>
              Save
            </Button>
            <Button variant="primary" icon="arrowRight" onClick={() => save(true)} loading={saving}>
              Save & continue
            </Button>
          </div>
        </div>
      </Card>

      <Card className="soft">
        <SectionHead eyebrow="Replace" title="Upload a different resume" />
        <Dropzone busy={busy} onFile={upload} />
      </Card>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete your data?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={remove}>
              Delete everything
            </Button>
          </>
        }
      >
        <p>
          This removes your resume text, profile, every search run, the shortlists and the outreach history.
          It cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
