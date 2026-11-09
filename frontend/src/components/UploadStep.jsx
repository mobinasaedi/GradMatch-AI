import { useState } from "react";
import { api } from "../api";

export default function UploadStep({ onUploaded }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      onUploaded(await api.uploadResume(file));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  return (
    <section className="card">
      <h2>Upload your resume</h2>
      <p className="muted">PDF or DOCX, up to 5 MB. Text is extracted locally on the server; no paid services are used.</p>
      <input type="file" accept=".pdf,.docx" onChange={onFile} disabled={busy} />
      {busy && <p>Reading your resume…</p>}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
